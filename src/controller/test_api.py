import os

import pytest

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN  # must be set before main is imported

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

client = TestClient(main.app)  # no "with": lifespan (poll loop) is skipped
GOOD = {"Authorization": "Bearer " + TOKEN}
VM = "vm-12345678"


def body(**over):
    b = {"name": "web01", "vcpus": 1, "memory_mb": 512, "disk_gb": 4}
    b.update(over)
    return b


def test_health_is_open():
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong-token-value"},
    {"Authorization": "Basic " + TOKEN},
    {"Authorization": "Bearer"},
])
def test_bad_credentials_rejected(headers):
    r = client.get("/nodes", headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path", [
    ("GET", "/nodes"),
    ("GET", "/vms"),
    ("POST", "/vms"),
    ("GET", "/vms/" + VM),
    ("POST", "/vms/" + VM + "/start"),
    ("POST", "/vms/" + VM + "/stop"),
    ("DELETE", "/vms/" + VM),
    ("GET", "/decisions"),
])
def test_every_route_needs_a_token(method, path):
    assert client.request(method, path).status_code == 401


def test_auth_is_checked_before_validation():
    r = client.post("/vms", json=body(vcpus=0))
    assert r.status_code == 401


@pytest.mark.parametrize("bad", [
    body(name="Web 01"),
    body(name=""),
    body(name="-web"),
    body(name="a" * 32),
    body(vcpus=0),
    body(vcpus=9),
    body(memory_mb=64),
    body(memory_mb=9000),
    body(disk_gb=0),
    body(disk_gb=51),
    {},
])
def test_invalid_create_requests_rejected(bad):
    r = client.post("/vms", json=bad, headers=GOOD)
    assert r.status_code == 422


@pytest.mark.parametrize("method,path", [
    ("GET", "/vms/vm-xxxxxxxx"),
    ("DELETE", "/vms/vm-123"),
    ("GET", "/nodes/NODE_A"),
])
def test_invalid_ids_rejected(method, path):
    assert client.request(method, path, headers=GOOD).status_code == 422
