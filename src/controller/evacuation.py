"""Self-healing and auto-evacuation engine for HA VMs."""
import concurrent.futures
import os
import threading
import time

import database as db
from scheduler import Decision, place
import vm_service as vs
import worker_client as wc
from worker_client import WorkerError, WorkerUnreachable

WorkerClient = wc.WorkerClient

DEFAULT_CONCURRENCY = 3
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_S = 5.0

_evac_lock = threading.Lock()


def get_evacuation_concurrency():
    try:
        return max(1, int(os.environ.get("PS023_EVACUATION_CONCURRENCY", DEFAULT_CONCURRENCY)))
    except (ValueError, TypeError):
        return DEFAULT_CONCURRENCY


def get_max_retries():
    try:
        return max(1, int(os.environ.get("PS023_EVACUATION_MAX_RETRIES", DEFAULT_MAX_RETRIES)))
    except (ValueError, TypeError):
        return DEFAULT_MAX_RETRIES


def get_backoff_s():
    try:
        return max(0.1, float(os.environ.get("PS023_EVACUATION_BACKOFF_S", DEFAULT_BACKOFF_S)))
    except (ValueError, TypeError):
        return DEFAULT_BACKOFF_S


def find_vms_needing_evacuation(path=None, now=None):
    """Find HA VMs that belong to UNHEALTHY nodes, or are stalled in EVACUATING / retrying EVACUATION_FAILED."""
    now = time.time() if now is None else now
    nodes_by_id = {n["id"]: n for n in db.list_nodes(path)}
    vms = db.list_vms(path)
    to_evacuate = []

    backoff = get_backoff_s()
    max_retries = get_max_retries()

    for vm in vms:
        if not vm.get("ha"):
            continue  # Non-HA VMs remain UNKNOWN or unchanged

        node = nodes_by_id.get(vm["node_id"])
        node_unhealthy = node is not None and node["status"] != "HEALTHY"

        status = vm.get("status")

        if node_unhealthy and status in ("RUNNING", "UNKNOWN"):
            to_evacuate.append(vm)
        elif status == "EVACUATING":
            to_evacuate.append(vm)
        elif status == "EVACUATION_FAILED":
            retries = vm.get("evacuation_retries") or 0
            started = vm.get("evacuation_started_at") or 0
            if retries < max_retries and (now - started) >= backoff:
                to_evacuate.append(vm)

    return to_evacuate


def _evacuate_single_vm(vm, path=None, now=None):
    now = time.time() if now is None else now
    vm_id = vm["id"]
    old_node_id = vm["node_id"]
    old_worker_vm_id = vm.get("worker_vm_id")
    started_at = vm.get("evacuation_started_at") or now
    retries = (vm.get("evacuation_retries") or 0) + 1

    # Mark evacuation started if not already
    if not vm.get("evacuation_started_at"):
        db.update_vm(vm_id, path, evacuation_started_at=started_at, status="EVACUATING")

    # Step 1: Select healthy node with capacity under atomic lock
    selected_node = None
    target_node_info = None
    target_free_mb = 0

    with vs._place_lock:
        views = vs.node_views(path)
        # Old node is either unhealthy or to be excluded
        decision = place(views, vm["memory_mb"])

        if decision.selected is None:
            reason = decision.reason or "no healthy node has enough memory"
            db.update_vm(
                vm_id, path,
                status="EVACUATION_FAILED",
                evacuation_retries=retries,
                evacuation_error=reason,
            )
            db.record_decision(
                Decision(None, f"evacuation failed for {vm_id}: {reason}", vm["memory_mb"], decision.candidates),
                vm_id=vm_id, path=path
            )
            return False

        selected_node = decision.selected
        target_node_info = db.get_node(selected_node, path)
        for c in decision.candidates:
            if c["node_id"] == selected_node:
                target_free_mb = c.get("available_mb", 0)

        # Atomic reservation on target node
        db.update_vm(
            vm_id, path,
            node_id=selected_node,
            status="EVACUATING",
            evacuation_retries=retries,
            evacuation_error=None,
        )

    # Step 2: Record tombstone for fencing old node upon recovery
    if old_worker_vm_id:
        db.add_tombstone(old_node_id, old_worker_vm_id, vm["name"], path=path)

    # Step 3: Spawn and start VM on target worker
    client_cls = getattr(vs, "WorkerClient", None) or WorkerClient
    client = client_cls(target_node_info["id"], target_node_info["url"])
    try:
        wvm = client.create_vm(
            name=vm["name"],
            vcpus=vm["vcpus"],
            memory_mb=vm["memory_mb"],
            disk_gb=vm["disk_gb"],
            start=True,
        )
    except (WorkerUnreachable, WorkerError) as err:
        err_msg = f"target worker {selected_node} rejected evacuation: {err}"
        db.update_vm(
            vm_id, path,
            status="EVACUATION_FAILED",
            evacuation_error=err_msg,
            evacuation_retries=retries,
        )
        db.record_decision(
            Decision(None, err_msg, vm["memory_mb"], []),
            vm_id=vm_id, path=path
        )
        return False
    finally:
        client.close()

    # Step 4: Finalize recovery
    finished_at = time.time()
    recovery_time = round(finished_at - started_at, 2)
    db.update_vm(
        vm_id, path,
        worker_vm_id=wvm["id"],
        status=wvm["status"].upper(),
        ip_address=wvm.get("ip"),
        recovery_time_s=recovery_time,
        evacuation_error=None,
    )

    # Step 5: Structured decision log
    structured_log = (
        f"{old_node_id} UNHEALTHY -> evacuating {vm_id} (ha) -> "
        f"placed on {selected_node} (free {target_free_mb} MB) -> "
        f"RUNNING in {recovery_time:.1f} s"
    )
    db.record_decision(
        Decision(
            selected=selected_node,
            reason=structured_log,
            requested_mb=vm["memory_mb"],
            candidates=[{"node_id": selected_node, "healthy": True, "verdict": "evacuated"}],
        ),
        vm_id=vm_id,
        path=path,
    )
    return True


def evacuate_unhealthy_vms(path=None, now=None):
    """Scan and evacuate eligible HA VMs with concurrency cap."""
    with _evac_lock:
        vms = find_vms_needing_evacuation(path, now)
        if not vms:
            return 0

        concurrency = get_evacuation_concurrency()
        evacuated_count = 0

        if concurrency == 1 or len(vms) == 1:
            for vm in vms:
                if _evacuate_single_vm(vm, path, now):
                    evacuated_count += 1
        else:
            max_workers = min(concurrency, len(vms))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_evacuate_single_vm, vm, path, now) for vm in vms]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        if future.result():
                            evacuated_count += 1
                    except Exception as e:
                        print("evacuation thread error:", repr(e), flush=True)

        return evacuated_count
