import time

import database as db
import reconcile as rc
import vm_service as vs
from conftest import REMOTE


def test_unhealthy_node_marks_vms_unknown(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    db.update_node("node-a", env, status="UNHEALTHY")
    rc.reconcile(env)
    assert db.get_vm(vm["id"], env)["status"] == "UNKNOWN"


def test_node_returns_and_vm_resyncs(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    db.update_node("node-a", env, status="UNHEALTHY")
    rc.reconcile(env)
    db.update_node("node-a", env, status="HEALTHY")
    rc.reconcile(env)
    assert db.get_vm(vm["id"], env)["status"] == "RUNNING"


def test_old_orphan_is_deleted(env):
    REMOTE["node-a"]["w-orphan"] = {"id": "w-orphan", "status": "running",
                                    "ip": None,
                                    "created_at": time.time() - 500}
    rc.reconcile(env)
    assert "w-orphan" not in REMOTE["node-a"]


def test_young_orphan_is_kept(env):
    REMOTE["node-a"]["w-new"] = {"id": "w-new", "status": "running",
                                 "ip": None, "created_at": time.time()}
    rc.reconcile(env)
    assert "w-new" in REMOTE["node-a"]


def test_stale_pending_row_fails(env):
    vm_id = db.add_vm("p1", "node-a", 1, 512, 4, "PENDING", path=env)
    rc.reconcile(env, now=time.time() + 200)
    assert db.get_vm(vm_id, env)["status"] == "FAILED"


def test_vm_gone_from_worker_fails(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    REMOTE["node-a"].clear()
    rc.reconcile(env, now=time.time() + 100)
    assert db.get_vm(vm["id"], env)["status"] == "FAILED"
