import pytest

import database as db
import vm_service as vs
from worker_client import WorkerError, WorkerUnreachable

BEHAVIOR = {}  # node id -> "ok" | "down" | ("refuse", detail) | ("error", code)


class FakeClient:
    def __init__(self, node_id, url, token=None):
        self.node_id = node_id

    def close(self):
        pass

    def create_vm(self, name, vcpus, memory_mb, disk_gb, start=True):
        b = BEHAVIOR.get(self.node_id, "ok")
        if b == "down":
            raise WorkerUnreachable(self.node_id)
        if isinstance(b, tuple):
            raise WorkerError(409 if b[0] == "refuse" else b[1], b[1])
        return {"id": "w-" + name, "status": "running", "ip": "10.0.0.9"}


@pytest.fixture
def dbp(tmp_path, monkeypatch):
    BEHAVIOR.clear()
    monkeypatch.setattr(vs, "WorkerClient", FakeClient)
    monkeypatch.setattr(vs.ns, "poll_all", lambda path=None: None)
    p = str(tmp_path / "t.db")
    db.init_db(p)
    for nid, mb in (("node-a", 9000), ("node-b", 2500)):
        db.upsert_node(nid, "http://x", p)
        db.update_node(nid, p, status="HEALTHY", memory_schedulable_mb=mb)
    return p


def test_more_memory_wins(dbp):
    assert vs.create_vm("w1", 1, 512, 4, path=dbp)["node_id"] == "node-a"


def test_refusal_falls_through(dbp):
    BEHAVIOR["node-a"] = ("refuse", "tapvm0 missing")
    assert vs.create_vm("w1", 1, 512, 4, path=dbp)["node_id"] == "node-b"


def test_both_refuse_reports_reasons(dbp):
    BEHAVIOR["node-a"] = ("refuse", "no TAP")
    BEHAVIOR["node-b"] = ("refuse", "no slot")
    with pytest.raises(vs.NoCapacity) as e:
        vs.create_vm("w1", 1, 512, 4, path=dbp)
    assert "node-a: no TAP" in str(e.value) and "node-b: no slot" in str(e.value)
    for c in e.value.decision.candidates:
        assert c["verdict"].startswith("refused:") and c["healthy"] is True
    assert db.list_vms(dbp) == []


def test_unreachable_worker_marked_unhealthy(dbp):
    BEHAVIOR["node-a"] = "down"
    vm = vs.create_vm("w1", 1, 512, 4, path=dbp)
    assert vm["node_id"] == "node-b"
    assert db.get_node("node-a", dbp)["status"] == "UNHEALTHY"
    assert len(db.list_vms(dbp)) == 1


def test_memory_is_reserved(dbp):
    db.update_node("node-a", dbp, status="UNHEALTHY")
    vs.create_vm("w1", 1, 2000, 4, path=dbp)
    with pytest.raises(vs.NoCapacity):
        vs.create_vm("w2", 1, 2000, 4, path=dbp)


def test_other_worker_error_is_rejected(dbp):
    BEHAVIOR["node-a"] = ("error", 500)
    with pytest.raises(vs.WorkerRejected):
        vs.create_vm("w1", 1, 512, 4, path=dbp)
    assert db.list_vms(dbp) == []
