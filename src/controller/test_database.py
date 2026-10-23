import pytest

import database as db
from scheduler import NodeView, place


@pytest.fixture
def path(tmp_path):
    p = str(tmp_path / "test.db")
    db.init_db(p)
    db.upsert_node("node-a", "http://127.0.0.1:8001", p)
    db.upsert_node("node-b", "http://127.0.0.1:8002", p)
    return p


def test_node_update_and_list(path):
    db.update_node("node-a", path, status="HEALTHY", memory_schedulable_mb=9000)
    assert db.get_node("node-a", path)["status"] == "HEALTHY"
    assert len(db.list_nodes(path)) == 2


def test_vm_lifecycle_rows(path):
    vm = db.add_vm("web01", "node-a", 2, 1024, 4, path=path)
    assert vm.startswith("vm-")
    assert db.get_vm(vm, path)["status"] == "PENDING"
    db.update_vm(vm, path, status="RUNNING", ip_address="192.168.100.10")
    assert db.get_vm(vm, path)["status"] == "RUNNING"
    db.delete_vm(vm, path)
    assert db.get_vm(vm, path) is None


def test_unknown_column_rejected(path):
    vm = db.add_vm("web01", "node-a", 2, 1024, 4, path=path)
    with pytest.raises(ValueError):
        db.update_vm(vm, path, bogus="x")


def test_foreign_key_enforced(path):
    with pytest.raises(Exception) as e:
        db.add_vm("ghost", "node-zzz", 1, 512, 4, path=path)
    assert "FOREIGN KEY" in str(e.value).upper()


def test_decision_recorded(path):
    vm = db.add_vm("web01", "node-a", 2, 1024, 4, path=path)
    d = place([NodeView("node-a", True, 9000), NodeView("node-b", True, 3000)], 2048)
    db.record_decision(d, vm, path)
    last = db.latest_decisions(1, path)[0]
    assert last["selected"] == "node-a" and len(last["candidates"]) == 2
