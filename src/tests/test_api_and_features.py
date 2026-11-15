import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath("controller"))

os.environ.setdefault("PS023_API_TOKEN", "test-token-0123456789abcdef")

import database as db
from scheduler import NodeView, place
from fastapi.testclient import TestClient
import main


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.init_db(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_scheduler_place_logic():
    A = NodeView("node-a", True, 10240)
    B = NodeView("node-b", True, 4096)
    d = place([A, B], 2048)
    assert d.selected == "node-a"
    assert len(d.candidates) == 2


def test_database_events(test_db):
    db.record_event("VM_CREATE", "Created vm-test", level="INFO", details={"name": "test"}, path=test_db)
    db.record_event("NODE_OFFLINE", "node-b is down", level="WARNING", path=test_db)

    events = db.latest_events(10, path=test_db)
    assert len(events) == 2
    assert events[0]["event_type"] == "NODE_OFFLINE"

    filtered = db.latest_events(10, level="WARNING", path=test_db)
    assert len(filtered) == 1
    assert filtered[0]["event_type"] == "NODE_OFFLINE"


def test_database_images(test_db):
    images = db.list_images(path=test_db)
    assert len(images) >= 7

    ubuntu = db.get_image("ubuntu-24-04", path=test_db)
    assert ubuntu is not None
    assert ubuntu["distro"] == "Ubuntu"

    # Add custom image
    db.upsert_image(
        image_id="custom-alpine",
        name="Alpine Linux 3.20",
        distro="Alpine",
        version="3.20",
        status="AVAILABLE",
        path=test_db
    )
    img = db.get_image("custom-alpine", path=test_db)
    assert img["name"] == "Alpine Linux 3.20"

    # Safe delete image
    db.delete_image("custom-alpine", path=test_db)
    assert db.get_image("custom-alpine", path=test_db) is None


def test_image_delete_protection_when_vm_active(test_db):
    db.upsert_node("node-a", "http://127.0.0.1:8001", test_db)
    db.upsert_image("test-img", "Test Image", "Test", "1.0", path=test_db)
    db.add_vm("test-vm", "node-a", 1, 512, 4, "RUNNING", path=test_db, image="test-img")

    with pytest.raises(ValueError, match="in use by VM"):
        db.delete_image("test-img", path=test_db)


def test_api_health():
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_auth_required():
    client = TestClient(main.app)
    resp = client.get("/nodes")
    assert resp.status_code == 401


def test_api_redirects():
    client = TestClient(main.app)
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dashboard/"

    resp = client.get("/terminals", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dashboard/#terminals"

    resp = client.get("/vms/vm-12345678/terminal-page", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dashboard/#terminals?vm_id=vm-12345678"


def test_node_metrics_storage_and_query(test_db):
    now = 1729000000.0
    db.upsert_node("node-a", "http://127.0.0.1:8001", path=test_db)
    db.record_node_metrics(
        node_id="node-a",
        timestamp=now,
        cpu_percent=14.5,
        memory_used_mb=2048,
        memory_total_mb=8192,
        memory_available_mb=6144,
        memory_percent=25.0,
        disk_used_mb=5000,
        disk_total_mb=20000,
        disk_percent=25.0,
        network_rx_kbps=12.4,
        network_tx_kbps=4.2,
        vms_running=1,
        path=test_db
    )
    samples = db.get_node_metrics("node-a", path=test_db)
    assert len(samples) == 1
    assert samples[0]["cpu_percent"] == 14.5
    assert samples[0]["memory_percent"] == 25.0
    assert samples[0]["network_rx_kbps"] == 12.4



def test_dashboard_static_files():
    client = TestClient(main.app)
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert "VM Controller" in resp.text
    assert '<div id="root"></div>' in resp.text


def test_authenticated_endpoints():
    token = os.environ.get("PS023_API_TOKEN", "default-test-token-ps023")
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(main.app)

    # 1. Images
    resp = client.get("/images", headers=headers)
    assert resp.status_code == 200
    imgs = resp.json()
    assert len(imgs) >= 7

    # 2. Events
    resp = client.get("/events", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 3. Terminal sessions
    resp = client.get("/terminal-sessions")
    assert resp.status_code == 200
    assert "active_sessions" in resp.json()

    # 4. Scheduler preview
    resp = client.post("/scheduler/preview", headers=headers, json={"memory_mb": 1024, "vcpus": 1})
    assert resp.status_code == 200
    preview = resp.json()
    assert "can_accommodate" in preview
    assert "nodes" in preview

    # 5. Image import validation check on bogus path
    resp = client.post("/images/import", headers=headers, json={
        "id": "nonexistent-img",
        "name": "Nonexistent",
        "distro": "Linux",
        "version": "1.0",
        "path": "/bogus/path/that/does/not/exist.raw"
    })
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "File not found" in detail or "Image path must reside" in detail
