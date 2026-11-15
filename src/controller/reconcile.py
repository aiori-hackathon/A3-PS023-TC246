"""Compare the controller's database with what the workers really run."""
import json
import time

import database as db
import evacuation as evac
from worker_client import WorkerClient, WorkerError, WorkerUnreachable

PENDING_TIMEOUT_S = 120  # a PENDING row older than this was abandoned
MISSING_GRACE_S = 60     # a young VM is never "missing": the worker list may be stale
ORPHAN_MIN_AGE_S = 120   # only remove unknown worker VMs older than this


def _log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] reconcile: {msg}", flush=True)


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
            cg = 1 if w.get("cgroups") else 0
            cg_lim = json.dumps(w.get("cgroup_limits")) if w.get("cgroup_limits") else None
            if (status != v["status"] or ip != v["ip_address"] or
                    bool(cg) != bool(v.get("cgroups")) or
                    cg_lim != (json.dumps(v.get("cgroup_limits")) if v.get("cgroup_limits") else None)):
                db.update_vm(v["id"], path, status=status, ip_address=ip,
                             cgroups=cg, cgroup_limits=cg_lim)
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


def _fence_stale_copies(node, remote, client, path):
    # 1. Check pending tombstones for this node
    tombstones = db.get_pending_tombstones(node["id"], path)
    for t in tombstones:
        wid_to_delete = None
        if t["worker_vm_id"] in remote:
            wid_to_delete = t["worker_vm_id"]
        else:
            for wid, w in list(remote.items()):
                if w.get("name") == t["vm_name"]:
                    wid_to_delete = wid
                    break
        if wid_to_delete:
            try:
                client.delete_vm(wid_to_delete)
                remote.pop(wid_to_delete, None)
                _log(f"fenced stale copy {wid_to_delete} ({t['vm_name']}) on recovered {node['id']}")
            except (WorkerUnreachable, WorkerError) as e:
                _log(f"could not fence stale copy {wid_to_delete}: {e}")
        db.mark_tombstone_fenced(t["id"], path)

    # 2. Check if any remote VM has the same name as an active HA VM on another node
    all_vms = db.list_vms(path)
    other_ha_vms = {
        v["name"]: v for v in all_vms
        if v.get("ha") and v["node_id"] != node["id"] and v["status"] in ("RUNNING", "EVACUATING")
    }
    for wid, w in list(remote.items()):
        name = w.get("name") or (wid[2:] if wid.startswith("w-") else wid)
        if name in other_ha_vms:
            try:
                client.delete_vm(wid)
                remote.pop(wid, None)
                _log(f"fenced duplicate stale VM {wid} ({name}) on {node['id']}")
            except (WorkerUnreachable, WorkerError) as e:
                _log(f"could not fence duplicate stale VM {wid}: {e}")


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
            _fence_stale_copies(node, remote, client, path)
            _sync_node(node, remote, client, path, now)
        finally:
            client.close()

    evac.evacuate_unhealthy_vms(path=path, now=now)
