import os

import pytest

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN  # same value as test_api.py

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import vm_service as vs  # noqa: E402
from scheduler import Decision  # noqa: E402

client = TestClient(main.app)
GOOD = {"Authorization": "Bearer " + TOKEN}
VM = "vm-12345678"
BODY = {"name": "web01", "vcpus": 1, "memory_mb": 512, "disk_gb": 4}


def raising(exc):
    def f(*a, **k):
        raise exc
    return f


def test_create_returns_201(monkeypatch):
    monkeypatch.setattr(main.svc, "create_vm", lambda *a: {"id": VM})
    r = client.post("/vms", json=BODY, headers=GOOD)
    assert r.status_code == 201 and r.json()["id"] == VM


def test_no_capacity_is_409_with_decision(monkeypatch):
    d = Decision(None, "no healthy node has enough memory", 512, [])
    monkeypatch.setattr(main.svc, "create_vm", raising(vs.NoCapacity(d)))
    r = client.post("/vms", json=BODY, headers=GOOD)
    assert r.status_code == 409
    assert r.json()["decision"]["requested_mb"] == 512


def test_node_unavailable_is_503(monkeypatch):
    monkeypatch.setattr(main.svc, "create_vm",
                        raising(vs.NodeUnavailable("node-a is unreachable")))
    assert client.post("/vms", json=BODY, headers=GOOD).status_code == 503


def test_worker_rejection_is_502(monkeypatch):
    monkeypatch.setattr(main.svc, "create_vm",
                        raising(vs.WorkerRejected(500, "boom")))
    assert client.post("/vms", json=BODY, headers=GOOD).status_code == 502


@pytest.mark.parametrize("method,path,fn", [
    ("GET", "/vms/" + VM, "get_vm"),
    ("POST", "/vms/" + VM + "/start", "start_vm"),
    ("POST", "/vms/" + VM + "/stop", "stop_vm"),
    ("DELETE", "/vms/" + VM, "delete_vm"),
])
def test_unknown_vm_is_404(monkeypatch, method, path, fn):
    monkeypatch.setattr(main.svc, fn, raising(vs.NotFound(VM)))
    assert client.request(method, path, headers=GOOD).status_code == 404


def test_delete_returns_204(monkeypatch):
    monkeypatch.setattr(main.svc, "delete_vm", lambda vm_id: None)
    assert client.delete("/vms/" + VM, headers=GOOD).status_code == 204


def test_unknown_node_is_404(monkeypatch):
    monkeypatch.setattr(main.db, "get_node", lambda node_id: None)
    assert client.get("/nodes/node-z", headers=GOOD).status_code == 404


@pytest.mark.parametrize("asked,used", [(0, 1), (500, 100), (20, 20)])
def test_decisions_limit_is_clamped(monkeypatch, asked, used):
    seen = []
    monkeypatch.setattr(main.db, "latest_decisions",
                        lambda limit: seen.append(limit) or [])
    r = client.get(f"/decisions?limit={asked}", headers=GOOD)
    assert r.status_code == 200 and seen == [used]
