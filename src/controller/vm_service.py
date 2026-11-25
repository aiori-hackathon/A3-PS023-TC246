"""VM operations: placement, worker calls, and bookkeeping."""
import json
import subprocess
import threading
from pathlib import Path

import database as db
import node_service as ns
from scheduler import NodeView, place
from worker_client import WorkerClient, WorkerError, WorkerUnreachable

_place_lock = threading.Lock()


def stage_image_for_node_b(image_id: str, db_path: str = None) -> bool:
    """Ensure image is available on Node B, syncing on-demand from Node A with free-space safety check."""
    if not image_id or image_id == "ubuntu-24-04":
        return True

    node_b = db.get_node("node-b", db_path)
    if node_b and (node_b.get("backend") == "azure" or "8012" in node_b.get("url", "") or "10.100.0." in node_b.get("url", "")):
        return False

    img = db.get_image(image_id, db_path)
    if not img or not img.get("path"):
        return False

    src_file = Path(img["path"])
    if not src_file.exists():
        return False

    filename = src_file.name
    node_b_host = "192.168.100.17"
    node_b_user = "rajyavardhan"
    node_b_dest_dir = f"/home/{node_b_user}/nested/images"

    # Check if already present on Node B
    check_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                 f"{node_b_user}@{node_b_host}", f"test -f {node_b_dest_dir}/{filename}"]
    if subprocess.run(check_cmd, capture_output=True).returncode == 0:
        return True

    # Check Node B free disk space (df -m /)
    df_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
              f"{node_b_user}@{node_b_host}", "df -m / | awk 'NR==2 {print $4}'"]
    proc = subprocess.run(df_cmd, capture_output=True, text=True)
    try:
        free_mb = int(proc.stdout.strip())
    except Exception:
        free_mb = 0

    # Evict unused images if free space is below 3000 MB
    if free_mb < 3000:
        vms = db.list_vms(db_path)
        active_b_images = {v["image"] for v in vms if v.get("node_id") == "node-b" and v.get("image")}
        ls_cmd = ["ssh", "-o", "BatchMode=yes", f"{node_b_user}@{node_b_host}", f"ls {node_b_dest_dir}"]
        out = subprocess.run(ls_cmd, capture_output=True, text=True).stdout.split()
        for f in out:
            if f != "ubuntu-noble.raw" and not any(f.startswith(img_id) for img_id in active_b_images):
                subprocess.run(["ssh", "-o", "BatchMode=yes", f"{node_b_user}@{node_b_host}", f"rm -f {node_b_dest_dir}/{f}"])

    # Perform sparse sync
    rsync_cmd = ["rsync", "-S", "--timeout=120", str(src_file), f"{node_b_user}@{node_b_host}:{node_b_dest_dir}/{filename}"]
    res = subprocess.run(rsync_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False

    # Sync initrd if present
    if img.get("initrd_path"):
        initrd_file = Path(img["initrd_path"])
        if initrd_file.exists():
            subprocess.run(["rsync", "-S", "--timeout=60", str(initrd_file), f"{node_b_user}@{node_b_host}:{node_b_dest_dir}/{initrd_file.name}"])

    return True


def cleanup_unused_image_on_node_b(image_id: str, db_path: str = None):
    """Evict a staged non-base image from Node B if no active VMs on Node B are using it."""
    if not image_id or image_id == "ubuntu-24-04":
        return
    vms = db.list_vms(db_path)
    still_in_use = any(v.get("node_id") == "node-b" and v.get("image") == image_id for v in vms)
    if not still_in_use:
        img = db.get_image(image_id, db_path)
        if img and img.get("path"):
            fname = Path(img["path"]).name
            subprocess.run(["ssh", "-o", "BatchMode=yes", "rajyavardhan@192.168.100.17",
                            f"rm -f /home/rajyavardhan/nested/images/{fname}"], capture_output=True)


class NotFound(Exception):
    pass


class ImageNotStaged(Exception):
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
        if vm["status"] in ("PENDING", "RUNNING", "UNKNOWN", "EVACUATING"):
            reserved[vm["node_id"]] = reserved.get(vm["node_id"], 0) + vm["memory_mb"]
    views = []
    for n in db.list_nodes(path):
        free = (n["memory_schedulable_mb"] or 0) - reserved.get(n["id"], 0)
        healthy = n["status"] == "HEALTHY" and n["id"] not in down
        views.append(NodeView(n["id"], healthy, max(0, free),
                              n["vms_running"] or 0))
    return views


def create_vm(name, vcpus, memory_mb, disk_gb=4, path=None,
              ha=False, image="ubuntu-24-04", user_data=None, tags=None,
              target_node=None, policy=None):
    ns.poll_all(path)
    down = set()  # nodes that failed during this request
    refused = {}  # node id -> why it failed, so the final error can say so
    while True:
        with _place_lock:
            decision = place(node_views(path, down), memory_mb, target_node=target_node, policy=policy)
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
                              "PENDING", path, ha=ha, image=image,
                              user_data=user_data, tags=tags)
            db.record_decision(decision, vm_id, path)

        if node["id"] == "node-b":
            if node.get("backend") == "azure" or "8012" in node.get("url", "") or "10.100.0." in node.get("url", ""):
                if image and image != "ubuntu-24-04":
                    db.delete_vm(vm_id, path)
                    raise ImageNotStaged(f"image '{image}' is not staged on Azure node B (only ubuntu-24-04 is available)")
            else:
                try:
                    stage_image_for_node_b(image, path)
                except Exception:
                    pass

        client = WorkerClient(node["id"], node["url"])
        try:
            try:
                wvm = client.create_vm(name, vcpus, memory_mb, disk_gb, image=image)
            except TypeError:
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

        fields = {
            "worker_vm_id": wvm["id"],
            "status": wvm["status"].upper(),
            "ip_address": wvm.get("ip"),
        }
        if "cgroups" in wvm:
            fields["cgroups"] = 1 if wvm["cgroups"] else 0
            fields["cgroup_limits"] = json.dumps(wvm["cgroup_limits"]) if wvm.get("cgroup_limits") else None
        db.update_vm(vm_id, path, **fields)
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
    fields = {
        "status": wvm["status"].upper(),
        "ip_address": wvm.get("ip"),
    }
    if "cgroups" in wvm:
        fields["cgroups"] = 1 if wvm["cgroups"] else 0
        fields["cgroup_limits"] = json.dumps(wvm["cgroup_limits"]) if wvm.get("cgroup_limits") else None
    db.update_vm(vm_id, path, **fields)
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
    if vm.get("node_id") == "node-b" and vm.get("image"):
        try:
            cleanup_unused_image_on_node_b(vm["image"], path)
        except Exception:
            pass


def get_vm(vm_id, path=None):
    return _require(vm_id, path)


def list_vms(path=None):
    return db.list_vms(path)
