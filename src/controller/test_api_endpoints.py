"""Real API integration tests covering endpoints, target_node, images, metrics, and events."""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN

import pytest
from fastapi.testclient import TestClient

import database as db
import main
import vm_service as svc
from worker_client import WorkerClient

AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def setup_api_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "controller.db")
    monkeypatch.setenv("PS023_DB", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Isolated images directory
    img_dir = tmp_path / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PS023_IMAGE_ROOT", str(img_dir))
    monkeypatch.setenv("PS023_IMAGES_DIR", str(img_dir))
    monkeypatch.setattr(main, "IMAGES_DIR", img_dir)
    monkeypatch.setenv("PS023_ALLOW_SMALL_IMAGES", "1")
    monkeypatch.setenv("PS023_TOKEN_NODE_A", "mock-token-a-123456789")
    monkeypatch.setenv("PS023_TOKEN_NODE_B", "mock-token-b-123456789")
    monkeypatch.setenv("PS023_TOKEN_NODE_C", "mock-token-c-123456789")
    monkeypatch.setattr(svc.ns, "poll_all", lambda path=None: None)
    db.init_db(test_db)

    # Seed nodes: node-a (healthy, 8192MB), node-b (healthy, 4096MB), node-c (unhealthy, 4096MB)
    db.upsert_node("node-a", "http://127.0.0.1:8001", path=test_db)
    db.update_node("node-a", path=test_db, status="HEALTHY", memory_total_mb=8192,
                   memory_schedulable_mb=8192, cpu_total=4, vms_running=0)

    db.upsert_node("node-b", "http://127.0.0.1:8002", path=test_db)
    db.update_node("node-b", path=test_db, status="HEALTHY", memory_total_mb=4096,
                   memory_schedulable_mb=4096, cpu_total=2, vms_running=0)

    db.upsert_node("node-c", "http://127.0.0.1:8003", path=test_db)
    db.update_node("node-c", path=test_db, status="UNHEALTHY", memory_total_mb=4096,
                   memory_schedulable_mb=4096, cpu_total=2, vms_running=0)

    # Mock WorkerClient.create_vm so network calls are intercepted without touching external workers
    def fake_create_vm(self, name, vcpus, memory_mb, disk_gb):
        return {
            "id": f"worker-vm-{name}",
            "name": name,
            "vcpus": vcpus,
            "memory_mb": memory_mb,
            "disk_gb": disk_gb,
            "status": "running",
            "ip": "192.168.100.50",
            "cgroups": True,
            "cgroup_limits": {"cpu_quota_us": 125000, "memory_max_bytes": 671088640, "pids_max": 256},
        }

    monkeypatch.setattr(WorkerClient, "create_vm", fake_create_vm)
    monkeypatch.setattr(WorkerClient, "resources", lambda self: {"status": "ok", "vms_running": 0})

    yield {"db": test_db, "images_dir": img_dir}


@pytest.fixture
def client():
    return TestClient(main.app)


# ---------- POST /vms & target_node tests ----------
def test_create_vm_auto_placement(client):
    body = {"name": "vm-auto", "vcpus": 1, "memory_mb": 512, "disk_gb": 4}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "vm-auto"
    assert data["status"] == "RUNNING"
    assert data["node_id"] == "node-a"  # highest available memory wins
    assert data["cgroups"] is True


def test_create_vm_pinned_target_node(client):
    body = {"name": "vm-pinned", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "target_node": "node-b"}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "vm-pinned"
    assert data["node_id"] == "node-b"


def test_create_vm_unknown_target_node_returns_422(client):
    body = {"name": "vm-bad-target", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "target_node": "node-unknown"}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 422
    assert "unknown target_node 'node-unknown'" in res.json()["detail"]


def test_create_vm_unhealthy_target_node_returns_409(client):
    body = {"name": "vm-unhealthy-target", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "target_node": "node-c"}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 409
    assert "target node node-c is unhealthy" in res.json()["detail"]


def test_create_vm_target_node_lacking_memory_returns_409(client):
    # node-b only has 4096 MB schedulable; request 6000 MB
    body = {"name": "vm-too-big", "vcpus": 1, "memory_mb": 6000, "disk_gb": 4, "target_node": "node-b"}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 409
    assert "target node node-b lacks memory" in res.json()["detail"]


def test_create_vm_invalid_body_returns_422(client):
    # Invalid memory (below minimum 128 MB)
    body = {"name": "vm-invalid", "vcpus": 1, "memory_mb": 32, "disk_gb": 4}
    res = client.post("/vms", json=body, headers=AUTH)
    assert res.status_code == 422


# ---------- /scheduler/preview tests ----------
def test_scheduler_preview_auto(client):
    body = {"memory_mb": 1024, "vcpus": 1, "target_node": "auto"}
    res = client.post("/scheduler/preview", json=body, headers=AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["can_accommodate"] is True
    assert data["recommended_node"] == "node-a"
    assert len(data["nodes"]) == 3


def test_scheduler_preview_pinned(client):
    body = {"memory_mb": 1024, "vcpus": 1, "target_node": "node-b"}
    res = client.post("/scheduler/preview", json=body, headers=AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["can_accommodate"] is True
    assert data["recommended_node"] == "node-b"


def test_scheduler_preview_unknown_target_node(client):
    body = {"memory_mb": 1024, "vcpus": 1, "target_node": "nonexistent-node"}
    res = client.post("/scheduler/preview", json=body, headers=AUTH)
    assert res.status_code == 422


def test_scheduler_preview_with_policies(client):
    # Preview with best_fit policy
    body = {"memory_mb": 1024, "vcpus": 1, "policy": "best_fit"}
    res = client.post("/scheduler/preview", json=body, headers=AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["policy"] == "best_fit"
    assert "policy_choices" in data
    assert "memory_aware" in data["policy_choices"]
    assert "first_fit" in data["policy_choices"]
    assert "best_fit" in data["policy_choices"]
    # Node B has 2048 schedulable, Node A has 6144 schedulable.
    # best_fit chooses Node B (smallest sufficient memory)
    assert data["policy_choices"]["best_fit"]["selected"] == "node-b"
    assert data["policy_choices"]["memory_aware"]["selected"] == "node-a"


# ---------- /images tests ----------
def test_images_list_and_get(client):
    res = client.get("/images", headers=AUTH)
    assert res.status_code == 200
    imgs = res.json()
    assert len(imgs) >= 7

    res = client.get("/images/ubuntu-24-04", headers=AUTH)
    assert res.status_code == 200
    assert res.json()["distro"] == "Ubuntu"


def test_images_delete_in_use_returns_409(client, setup_api_env):
    test_db = setup_api_env["db"]
    # Register custom image and link a VM to it
    db.upsert_image("in-use-img", "In Use Image", "Linux", path=test_db)
    db.add_vm("test-vm", "node-a", 1, 512, 4, "RUNNING", path=test_db, image="in-use-img")

    res = client.delete("/images/in-use-img", headers=AUTH)
    assert res.status_code == 409
    assert "in use by VM" in res.json()["detail"]


def test_images_import_path_traversal_rejected(client, setup_api_env):
    img_dir = setup_api_env["images_dir"]
    # 1. Reject '..' sequence in relative and nested path
    res = client.post("/images/import", json={
        "id": "traversal-1",
        "name": "Traversal Test",
        "distro": "Linux",
        "version": "1.0",
        "path": "../../etc/shadow",
    }, headers=AUTH)
    assert res.status_code == 400
    assert "Path traversal not allowed" in res.json()["detail"]

    # 2. Reject '..' embedded in path within images dir
    res2 = client.post("/images/import", json={
        "id": "traversal-2",
        "name": "Traversal Test 2",
        "distro": "Linux",
        "version": "1.0",
        "path": f"{img_dir}/../secret.txt",
    }, headers=AUTH)
    assert res2.status_code == 400
    assert "Path traversal not allowed" in res2.json()["detail"]


def test_images_import_symlink_rejected(client, setup_api_env):
    img_dir = setup_api_env["images_dir"]
    target_file = img_dir / "real.raw"
    target_file.write_bytes(b"A" * 1024)
    symlink_file = img_dir / "symlink.raw"
    symlink_file.symlink_to(target_file)

    res = client.post("/images/import", json={
        "id": "symlink-img",
        "name": "Symlink Test",
        "distro": "Linux",
        "version": "1.0",
        "path": str(symlink_file),
    }, headers=AUTH)
    assert res.status_code == 400
    assert "Symlinks are not allowed" in res.json()["detail"]


def test_images_import_symlink_pointing_outside_rejected(client, setup_api_env, tmp_path):
    img_dir = setup_api_env["images_dir"]
    outside_file = tmp_path / "outside-target.raw"
    outside_file.write_bytes(b"OUTSIDE_SECRET_DATA")
    symlink_inside = img_dir / "symlink_pointing_out.raw"
    symlink_inside.symlink_to(outside_file)

    res = client.post("/images/import", json={
        "id": "symlink-out",
        "name": "Symlink Outside Test",
        "distro": "Linux",
        "version": "1.0",
        "path": str(symlink_inside),
    }, headers=AUTH)
    assert res.status_code == 400
    # Must be rejected either as symlink or as outside configured images dir
    assert ("Symlinks are not allowed" in res.json()["detail"] or
            "must reside inside configured images directory" in res.json()["detail"])


def test_images_import_outside_images_dir_rejected(client, tmp_path):
    outside_file = tmp_path / "outside.raw"
    outside_file.write_bytes(b"B" * 1024)

    res = client.post("/images/import", json={
        "id": "outside-img",
        "name": "Outside Test",
        "distro": "Linux",
        "version": "1.0",
        "path": str(outside_file),
    }, headers=AUTH)
    assert res.status_code == 400
    assert "must reside inside configured images directory" in res.json()["detail"]


def test_images_import_expected_sha256_match(client, setup_api_env):
    import hashlib
    img_dir = setup_api_env["images_dir"]
    valid_file = img_dir / "custom-os-match.raw"
    raw_bytes = b"VERIFIED_BOOT_DATA_BYTES" * 64
    valid_file.write_bytes(raw_bytes)
    real_hash = hashlib.sha256(raw_bytes).hexdigest()

    res = client.post("/images/import", json={
        "id": "custom-os-match",
        "name": "Custom OS Match",
        "distro": "Custom",
        "version": "2.0",
        "path": str(valid_file),
        "format": "raw",
        "expected_sha256": real_hash,
    }, headers=AUTH)
    assert res.status_code == 201
    img = res.json()
    assert img["id"] == "custom-os-match"
    assert img["verification_status"] == "VERIFIED"
    assert img["checksum"] == f"sha256:{real_hash}"
    assert not img["checksum"].startswith("size:")


def test_images_import_expected_sha256_mismatch(client, setup_api_env):
    import hashlib
    img_dir = setup_api_env["images_dir"]
    valid_file = img_dir / "custom-os-mismatch.raw"
    raw_bytes = b"REAL_FILE_CONTENT_BYTES" * 64
    valid_file.write_bytes(raw_bytes)
    real_hash = hashlib.sha256(raw_bytes).hexdigest()
    wrong_hash = "0" * 64

    res = client.post("/images/import", json={
        "id": "custom-os-mismatch",
        "name": "Custom OS Mismatch",
        "distro": "Custom",
        "version": "2.0",
        "path": str(valid_file),
        "format": "raw",
        "expected_sha256": wrong_hash,
    }, headers=AUTH)
    assert res.status_code == 201
    img = res.json()
    assert img["id"] == "custom-os-mismatch"
    assert img["verification_status"] == "UNVERIFIED"
    assert img["checksum"] == f"sha256:{real_hash}"
    assert not img["checksum"].startswith("size:")


def test_images_import_omitted_expected_sha256(client, setup_api_env):
    import hashlib
    img_dir = setup_api_env["images_dir"]
    valid_file = img_dir / "custom-os-omitted.raw"
    raw_bytes = b"UNVERIFIED_DEFAULT_BYTES" * 64
    valid_file.write_bytes(raw_bytes)
    real_hash = hashlib.sha256(raw_bytes).hexdigest()

    res = client.post("/images/import", json={
        "id": "custom-os-omitted",
        "name": "Custom OS Omitted",
        "distro": "Custom",
        "version": "2.0",
        "path": str(valid_file),
        "format": "raw",
    }, headers=AUTH)
    assert res.status_code == 201
    img = res.json()
    assert img["id"] == "custom-os-omitted"
    assert img["verification_status"] == "UNVERIFIED"
    assert img["checksum"] == f"sha256:{real_hash}"
    assert not img["checksum"].startswith("size:")


# ---------- /events, /metrics, /terminal-sessions tests ----------
def test_events_endpoint(client, setup_api_env):
    test_db = setup_api_env["db"]
    db.record_event("TEST_EVENT", "Integration test event message", level="INFO", path=test_db)

    res = client.get("/events", headers=AUTH)
    assert res.status_code == 200
    events = res.json()
    assert any(e["event_type"] == "TEST_EVENT" for e in events)


def test_node_and_cluster_metrics_endpoints(client, setup_api_env):
    test_db = setup_api_env["db"]
    now = 1729000000.0
    db.record_node_metrics(
        node_id="node-a",
        timestamp=now,
        cpu_percent=15.0,
        memory_used_mb=2048,
        memory_total_mb=8192,
        memory_available_mb=6144,
        memory_percent=25.0,
        disk_used_mb=5000,
        disk_total_mb=20000,
        disk_percent=25.0,
        network_rx_kbps=10.0,
        network_tx_kbps=5.0,
        vms_running=1,
        path=test_db,
    )

    res = client.get("/nodes/node-a/metrics", headers=AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["node_id"] == "node-a"
    assert data["sample_count"] == 1
    assert data["metrics"][0]["cpu_percent"] == 15.0

    res = client.get("/cluster/metrics", headers=AUTH)
    assert res.status_code == 200
    cdata = res.json()
    assert cdata["total_nodes"] == 3
    assert cdata["healthy_nodes"] == 2
    assert cdata["total_memory_mb"] == 8192 + 4096


def test_terminal_sessions_endpoint(client):
    res = client.get("/terminal-sessions")
    assert res.status_code == 200
    data = res.json()
    assert data["active_sessions"] == 0
    assert data["max_sessions"] == 5
