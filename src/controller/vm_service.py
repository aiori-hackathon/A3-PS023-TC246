"""VM operations: placement, worker calls, and bookkeeping."""
import threading

import database as db
import node_service as ns
from scheduler import NodeView, place
from worker_client import WorkerClient, WorkerError, WorkerUnreachable

_place_lock = threading.Lock()


class NotFound(Exception):
    pass


class NoCapacity(Exception):
    def __init__(self, decision):
        super().__init__(decision.reason)
        self.decision = decision


class NodeUnavailable(Exception):
    pass


class WorkerRejected(Exception):
    def __init__(self, status, detail):
        super().__init__(f"worker said HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def node_views(path=None, down=()):
    reserved = {}
    for vm in db.list_vms(path):
        if vm["status"] in ("PENDING", "RUNNING", "UNKNOWN"):
            reserved[vm["node_id"]] = reserved.get(vm["node_id"], 0) + vm["memory_mb"]
    views = []
    for n in db.list_nodes(path):
        free = (n["memory_schedulable_mb"] or 0) - reserved.get(n["id"], 0)
        healthy = n["status"] == "HEALTHY" and n["id"] not in down
        views.append(NodeView(n["id"], healthy, max(0, free),
                              n["vms_running"] or 0))
    return views


def create_vm(name, vcpus, memory_mb, disk_gb=4, path=None):
    ns.poll_all(path)
    down = set()  # nodes that failed during this request
    refused = {}  # node id -> why it failed, so the final error can say so
    while True:
        with _place_lock:
            decision = place(node_views(path, down), memory_mb)
            for c in decision.candidates:
                why = refused.get(c["node_id"])
                if why:
                    c["verdict"] = "refused: " + why
                    c["healthy"] = why != "unreachable"
            if decision.selected is None:
                if refused:
                    decision.reason = "no node accepted the VM: " + "; ".join(
                        f"{n}: {r}" for n, r in refused.items())
                db.record_decision(decision, None, path)
                raise NoCapacity(decision)
            node = db.get_node(decision.selected, path)
            vm_id = db.add_vm(name, node["id"], vcpus, memory_mb, disk_gb,
                              "PENDING", path)
            db.record_decision(decision, vm_id, path)

        client = WorkerClient(node["id"], node["url"])
        try:
            wvm = client.create_vm(name, vcpus, memory_mb, disk_gb)
        except WorkerUnreachable:
            # NOTE: after a timeout the worker may have created the VM anyway.
            # The row is dropped here; a later reconcile step removes orphans.
            db.delete_vm(vm_id, path)
            db.update_node(node["id"], path, status="UNHEALTHY")
            refused[node["id"]] = "unreachable"
            down.add(node["id"])
            continue
        except WorkerError as e:
            db.delete_vm(vm_id, path)
            if e.status == 409:  # worker refused: try another node
                refused[node["id"]] = str(e.detail)
                down.add(node["id"])
                continue
            raise WorkerRejected(e.status, e.detail) from e
        finally:
            client.close()

        db.update_vm(vm_id, path, worker_vm_id=wvm["id"],
                     status=wvm["status"].upper(), ip_address=wvm.get("ip"))
        return db.get_vm(vm_id, path)


def _require(vm_id, path):
    vm = db.get_vm(vm_id, path)
    if vm is None:
        raise NotFound(vm_id)
    return vm


def _call(vm, action, path):
    node = db.get_node(vm["node_id"], path)
    client = WorkerClient(node["id"], node["url"])
    try:
        return getattr(client, action)(vm["worker_vm_id"])
    except WorkerUnreachable as e:
        raise NodeUnavailable(f"{node['id']} is unreachable") from e
    except WorkerError as e:
        raise WorkerRejected(e.status, e.detail) from e
    finally:
        client.close()


def _sync(vm_id, wvm, path):
    db.update_vm(vm_id, path, status=wvm["status"].upper(),
                 ip_address=wvm.get("ip"))
    return db.get_vm(vm_id, path)


def start_vm(vm_id, path=None):
    vm = _require(vm_id, path)
    return _sync(vm_id, _call(vm, "start_vm", path), path)


def stop_vm(vm_id, path=None):
    vm = _require(vm_id, path)
    return _sync(vm_id, _call(vm, "stop_vm", path), path)


def delete_vm(vm_id, path=None):
    vm = _require(vm_id, path)
    try:
        _call(vm, "delete_vm", path)
    except WorkerRejected as e:
        if e.status != 404:  # 404 means the worker no longer has it: fine
            raise
    db.delete_vm(vm_id, path)


def get_vm(vm_id, path=None):
    return _require(vm_id, path)


def list_vms(path=None):
    return db.list_vms(path)
