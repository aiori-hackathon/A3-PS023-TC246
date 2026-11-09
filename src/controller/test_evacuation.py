"""Tests for self-healing and auto-evacuation engine."""
import time
import pytest

from conftest import DOWN, REMOTE
import database as db
import evacuation as evac
import reconcile as rc
import vm_service as vs


def _move_to_node_b(vm, env):
    old_node = vm["node_id"]
    wid = f"w-{vm['name']}"
    if old_node != "node-b":
        db.update_vm(vm["id"], env, node_id="node-b")
        if wid in REMOTE[old_node]:
            REMOTE["node-b"][wid] = REMOTE[old_node].pop(wid)


def test_ha_vm_evacuates_non_ha_stays_unknown(env):
    """HA VM on a failed node is respawned on the healthy node; non-HA VM is not."""
    vm_ha = vs.create_vm("ha01", 1, 512, 4, path=env, ha=True)
    vm_non = vs.create_vm("non01", 1, 512, 4, path=env, ha=False)

    # Move them to node-b to simulate they were running there
    _move_to_node_b(vm_ha, env)
    _move_to_node_b(vm_non, env)

    # Fail node-b
    db.update_node("node-b", env, status="UNHEALTHY")
    DOWN.add("node-b")

    # Trigger reconcile / evacuation
    rc.reconcile(env)

    # Check non-HA VM: stays UNKNOWN
    non_updated = db.get_vm(vm_non["id"], env)
    assert non_updated["status"] == "UNKNOWN"
    assert non_updated["node_id"] == "node-b"

    # Check HA VM: evacuated to node-a, status RUNNING
    ha_updated = db.get_vm(vm_ha["id"], env)
    assert ha_updated["status"] == "RUNNING"
    assert ha_updated["node_id"] == "node-a"
    assert ha_updated["recovery_time_s"] is not None
    assert "w-ha01" in REMOTE["node-a"]

    # Verify structured decision log
    decisions = db.latest_decisions(limit=5, path=env)
    assert any("node-b UNHEALTHY -> evacuating" in d["reason"] for d in decisions)


def test_no_capacity_evacuation_failed_and_retries(env, monkeypatch):
    """No capacity on the healthy node -> EVACUATION_FAILED with a reason, and retries then stops."""
    vm_ha = vs.create_vm("ha-big", 2, 2048, 4, path=env, ha=True)
    _move_to_node_b(vm_ha, env)

    # Exhaust node-a schedulable memory
    db.update_node("node-a", env, memory_schedulable_mb=500)

    # Mark node-b UNHEALTHY
    db.update_node("node-b", env, status="UNHEALTHY")
    DOWN.add("node-b")

    monkeypatch.setenv("PS023_EVACUATION_MAX_RETRIES", "2")
    monkeypatch.setenv("PS023_EVACUATION_BACKOFF_S", "0.1")

    # Run reconcile: first attempt fails due to capacity
    rc.reconcile(env)
    vm = db.get_vm(vm_ha["id"], env)
    assert vm["status"] == "EVACUATION_FAILED"
    assert "no healthy node has enough memory" in vm["evacuation_error"]
    assert vm["evacuation_retries"] == 1

    # Wait for backoff to expire
    time.sleep(0.15)
    rc.reconcile(env)
    vm = db.get_vm(vm_ha["id"], env)
    assert vm["status"] == "EVACUATION_FAILED"
    assert vm["evacuation_retries"] == 2

    # Third attempt exceeds max_retries (2), should not retry
    time.sleep(0.15)
    rc.reconcile(env)
    vm = db.get_vm(vm_ha["id"], env)
    assert vm["status"] == "EVACUATION_FAILED"
    assert vm["evacuation_retries"] == 2  # stopped retrying


def test_controller_restart_mid_evacuation_no_duplicate(env):
    """Controller restart mid-evacuation does not duplicate the VM."""
    vm_ha = vs.create_vm("ha-restart", 1, 512, 4, path=env, ha=True)
    _move_to_node_b(vm_ha, env)
    db.update_vm(vm_ha["id"], env, status="EVACUATING", evacuation_started_at=time.time())

    db.update_node("node-b", env, status="UNHEALTHY")
    DOWN.add("node-b")

    # Evacuation picks up EVACUATING VM and finishes placing on node-a
    rc.reconcile(env)
    vm = db.get_vm(vm_ha["id"], env)
    assert vm["status"] == "RUNNING"
    assert vm["node_id"] == "node-a"
    assert len([w for w in REMOTE["node-a"].values() if w["name"] == "ha-restart"]) == 1

    # Re-running reconcile (simulating another loop after restart) does not spawn a second instance
    rc.reconcile(env)
    assert len([w for w in REMOTE["node-a"].values() if w["name"] == "ha-restart"]) == 1


def test_failed_node_returns_stale_copy_fenced(env):
    """Failed node returns -> the stale copy is stopped and not double-counted."""
    vm_ha = vs.create_vm("ha-fence", 1, 512, 4, path=env, ha=True)
    _move_to_node_b(vm_ha, env)

    # node-b fails
    db.update_node("node-b", env, status="UNHEALTHY")
    DOWN.add("node-b")

    # Evacuate to node-a
    rc.reconcile(env)
    vm = db.get_vm(vm_ha["id"], env)
    assert vm["node_id"] == "node-a"
    assert vm["status"] == "RUNNING"

    # node-b comes back online with the old stale copy still in its memory
    DOWN.discard("node-b")
    db.update_node("node-b", env, status="HEALTHY")
    # Verify stale copy is in node-b's remote before reconcile
    assert "w-ha-fence" in REMOTE["node-b"]

    # Reconcile should fence (delete) the stale copy from node-b
    rc.reconcile(env)
    assert "w-ha-fence" not in REMOTE["node-b"]
    # Live copy on node-a remains RUNNING
    assert "w-ha-fence" in REMOTE["node-a"]
    live_vm = db.get_vm(vm_ha["id"], env)
    assert live_vm["node_id"] == "node-a"
    assert live_vm["status"] == "RUNNING"


def test_concurrency_cap_and_no_oversubscription(env, monkeypatch):
    """Concurrency cap is respected; memory reservations do not oversubscribe."""
    monkeypatch.setenv("PS023_EVACUATION_CONCURRENCY", "2")

    # node-a has 9000 MB schedulable. Let's set it to 1200 MB
    db.update_node("node-a", env, memory_schedulable_mb=1200)

    # Create 3 HA VMs of 500 MB each on node-b
    vms = []
    for i in range(3):
        v = vs.create_vm(f"conc{i}", 1, 500, 4, path=env, ha=True)
        _move_to_node_b(v, env)
        vms.append(v["id"])

    # Node B fails
    db.update_node("node-b", env, status="UNHEALTHY")
    DOWN.add("node-b")

    rc.reconcile(env)

    # 1200 MB on node-a can only fit 2 VMs of 500 MB (1000 MB). The 3rd must fail due to capacity.
    results = [db.get_vm(vid, env) for vid in vms]
    running_on_a = [v for v in results if v["status"] == "RUNNING" and v["node_id"] == "node-a"]
    failed = [v for v in results if v["status"] == "EVACUATION_FAILED"]

    assert len(running_on_a) == 2
    assert len(failed) == 1
    assert "no healthy node has enough memory" in failed[0]["evacuation_error"]


def test_migration_is_idempotent(tmp_path):
    """Migration is idempotent (running twice does not error)."""
    p = str(tmp_path / "migrate.db")
    # First initialization
    db.init_db(p)
    # Second initialization
    db.init_db(p)

    # Verify tables and columns
    vms = db.list_vms(p)
    assert vms == []
    nodes = db.list_nodes(p)
    assert nodes == []
