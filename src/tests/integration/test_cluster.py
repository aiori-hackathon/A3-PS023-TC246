import os
import subprocess
import uuid

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PS023_INTEGRATION") != "1",
    reason="needs a running cluster: set PS023_INTEGRATION=1")

BASE = os.environ.get("PS023_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("PS023_API_TOKEN", "")


@pytest.fixture(scope="module")
def api():
    c = httpx.Client(base_url=BASE, timeout=120,
                     headers={"Authorization": "Bearer " + TOKEN})
    yield c
    c.close()


@pytest.fixture
def made(api):
    ids = []
    yield ids
    for i in ids:  # clean up even if the test failed
        api.delete(f"/vms/{i}")


def vmm_count():
    out = subprocess.run(["pgrep", "-fa", "[c]loud-hypervisor"],
                         capture_output=True, text=True).stdout
    return len(out.splitlines())


def new_name():
    return "itest-" + uuid.uuid4().hex[:6]


def test_health_open_and_auth_required():
    assert httpx.get(BASE + "/health").status_code == 200
    assert httpx.get(BASE + "/nodes").status_code == 401


def test_both_nodes_healthy(api):
    nodes = {n["id"]: n for n in api.get("/nodes").json()}
    assert set(nodes) == {"node-a", "node-b"}
    assert all(n["status"] == "HEALTHY" for n in nodes.values())


def test_lifecycle_placement_and_no_leak(api, made):
    before = vmm_count()
    r = api.post("/vms", json={"name": new_name(), "vcpus": 1,
                               "memory_mb": 512, "disk_gb": 4})
    assert r.status_code == 201, r.text
    vm = r.json()
    made.append(vm["id"])
    assert vm["status"] == "RUNNING"

    d = api.get("/decisions?limit=1").json()[0]
    assert len(d["candidates"]) == 2
    eligible = [c for c in d["candidates"] if c["verdict"] == "eligible"]
    best = max(eligible, key=lambda c: (c["available_mb"], c["node_id"]))
    assert d["selected"] == vm["node_id"] == best["node_id"]

    assert api.post(f"/vms/{vm['id']}/stop").json()["status"] == "STOPPED"
    assert api.post(f"/vms/{vm['id']}/start").json()["status"] == "RUNNING"
    assert api.delete(f"/vms/{vm['id']}").status_code == 204
    assert api.get(f"/vms/{vm['id']}").status_code == 404
    assert vm["id"] not in [v["id"] for v in api.get("/vms").json()]
    assert vmm_count() == before


def test_insufficient_memory_is_409_with_decision(api):
    top = max(n["memory_schedulable_mb"] for n in api.get("/nodes").json())
    if top >= 8192:
        pytest.skip("a node can fit the largest allowed VM right now")
    name = new_name()
    r = api.post("/vms", json={"name": name, "vcpus": 1,
                               "memory_mb": 8192, "disk_gb": 4})
    assert r.status_code == 409
    dec = r.json()["decision"]
    assert dec["selected"] is None and len(dec["candidates"]) == 2
    assert name not in [v["name"] for v in api.get("/vms").json()]
