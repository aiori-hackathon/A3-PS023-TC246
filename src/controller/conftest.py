import time

import pytest

import database as db
import reconcile as rc
import vm_service as vs
from worker_client import WorkerError, WorkerUnreachable

REMOTE = {}   # node id -> {worker vm id -> vm dict}
DOWN = set()  # node ids whose worker is "unreachable"


class Fake:
    def __init__(self, node_id, url, token=None):
        self.n = node_id

    def close(self):
        pass

    def _up(self):
        if self.n in DOWN:
            raise WorkerUnreachable(self.n)

    def _vm(self, wid):
        v = REMOTE[self.n].get(wid)
        if v is None:
            raise WorkerError(404, "no such vm")
        return v

    def create_vm(self, name, vcpus, memory_mb, disk_gb, start=True):
        self._up()
        wid = "w-" + name
        REMOTE[self.n][wid] = {"id": wid, "status": "running",
                               "ip": "10.0.0.9", "created_at": time.time()}
        return REMOTE[self.n][wid]

    def start_vm(self, wid):
        self._up()
        v = self._vm(wid)
        v["status"] = "running"
        return v

    def stop_vm(self, wid):
        self._up()
        v = self._vm(wid)
        v["status"] = "stopped"
        return v

    def delete_vm(self, wid):
        self._up()
        self._vm(wid)
        del REMOTE[self.n][wid]

    def list_vms(self):
        self._up()
        return list(REMOTE[self.n].values())


@pytest.fixture
def env(tmp_path, monkeypatch):
    REMOTE.clear()
    DOWN.clear()
    REMOTE.update({"node-a": {}, "node-b": {}})
    for mod in (vs, rc):
        monkeypatch.setattr(mod, "WorkerClient", Fake)
    monkeypatch.setattr(vs.ns, "poll_all", lambda path=None: None)
    p = str(tmp_path / "t.db")
    db.init_db(p)
    for nid, mb in (("node-a", 9000), ("node-b", 2500)):
        db.upsert_node(nid, "http://x", p)
        db.update_node(nid, p, status="HEALTHY", memory_schedulable_mb=mb)
    return p
