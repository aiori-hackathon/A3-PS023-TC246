"""Compare the controller's database with what the workers really run."""
import time

import database as db
from worker_client import WorkerClient, WorkerError, WorkerUnreachable

PENDING_TIMEOUT_S = 120  # a PENDING row older than this was abandoned
MISSING_GRACE_S = 60     # a young VM is never "missing": the worker list may be stale
ORPHAN_MIN_AGE_S = 120   # only remove unknown worker VMs older than this


def _log(msg):
    print("reconcile:", msg, flush=True)


def _mark_unknown(node, path):
    for v in db.list_vms(path):
        if v["node_id"] == node["id"] and v["status"] in ("RUNNING", "STOPPED"):
            db.update_vm(v["id"], path, status="UNKNOWN")
            _log(f"{v['id']} -> UNKNOWN ({node['id']} is unhealthy)")


def _sync_node(node, remote, client, path, now):
    mine = [v for v in db.list_vms(path) if v["node_id"] == node["id"]]
    known = {v["worker_vm_id"] for v in mine if v["worker_vm_id"]}
    pending_recent = False
    for v in mine:
        age = now - v["created_at"]
        wid = v["worker_vm_id"]
        if v["status"] == "PENDING":
            if age > PENDING_TIMEOUT_S:
                db.update_vm(v["id"], path, status="FAILED")
                _log(f"{v['id']} was PENDING too long -> FAILED")
            else:
                pending_recent = True
        elif wid in remote:
            w = remote[wid]
            status = w["status"].upper()
            ip = w.get("ip")
            if status != v["status"] or ip != v["ip_address"]:
                db.update_vm(v["id"], path, status=status, ip_address=ip)
                _log(f"{v['id']} synced from {node['id']}: {status}")
        elif wid and age > MISSING_GRACE_S and v["status"] != "FAILED":
            db.update_vm(v["id"], path, status="FAILED")
            _log(f"{v['id']} is gone from {node['id']} -> FAILED")
    if pending_recent:
        return  # a create is in flight: its VM would look like an orphan
    for wid, w in remote.items():
        if wid not in known and now - w["created_at"] > ORPHAN_MIN_AGE_S:
            try:
                client.delete_vm(wid)
                _log(f"removed orphan {wid} from {node['id']}")
            except (WorkerUnreachable, WorkerError) as e:
                _log(f"could not remove orphan {wid}: {e}")


def reconcile(path=None, now=None):
    now = time.time() if now is None else now
    for node in db.list_nodes(path):
        if node["status"] != "HEALTHY":
            _mark_unknown(node, path)
            continue
        client = WorkerClient(node["id"], node["url"])
        try:
            try:
                remote = {w["id"]: w for w in client.list_vms()}
            except (WorkerUnreachable, WorkerError):
                continue
            _sync_node(node, remote, client, path, now)
        finally:
            client.close()
