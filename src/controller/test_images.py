"""Tests for OS Image Catalog, Alpine 3.20 & CirrOS 0.6.2 metadata, and delete protection."""
import os
import pytest
from fastapi.testclient import TestClient

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN

import database as db
import main
import node_service as ns
from worker_client import WorkerClient

AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "controller.db")
    monkeypatch.setenv("PS023_DB", test_db)
    monkeypatch.setenv("PS023_TOKEN_NODE_A", "test-token-node-a")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(ns, "poll_all", lambda *args, **kwargs: {})
    db.init_db(test_db)

    # Seed a healthy node for VM creation tests
    db.upsert_node("node-a", "http://127.0.0.1:8001", path=test_db)
    db.update_node("node-a", path=test_db, status="HEALTHY", memory_total_mb=8192,
                   memory_schedulable_mb=6144, cpu_total=4,
                   last_heartbeat=1700000000.0, vms_running=0)


def test_image_catalog_includes_alpine_and_cirros():
    client = TestClient(main.app)
    res = client.get("/images", headers=AUTH)
    assert res.status_code == 200
    images = res.json()
    img_map = {img["id"]: img for img in images}

    # Verify Alpine 3.20 catalog entry
    assert "alpine-3-20" in img_map
    alpine = img_map["alpine-3-20"]
    assert alpine["distro"] == "Alpine"
    assert alpine["version"] == "3.20.3"
    assert "81df854fbd7327d293c726b1eeeb82061d3bc8f5a86a6f77eea720f6be372261" in alpine["checksum"]
    assert alpine["download_url"].startswith("https://dl-cdn.alpinelinux.org/alpine/v3.20/")
    assert alpine["kernel_path"] == "/boot/vmlinuz-virt"
    assert alpine["initrd_path"] == "/boot/initramfs-virt"
    assert "console=ttyS0 root=/dev/vda1" in alpine["cmdline"]
    assert "not boot-tested" in alpine["notes"].lower()

    # Verify CirrOS 0.6.2 catalog entry
    assert "cirros-0-6-2" in img_map
    cirros = img_map["cirros-0-6-2"]
    assert cirros["distro"] == "CirrOS"
    assert cirros["version"] == "0.6.2"
    assert "c8fc807773e5354afe61636071771906" in cirros["checksum"]
    assert "md5:" in cirros["checksum"]
    assert cirros["download_url"].startswith("https://download.cirros-cloud.net/0.6.2/")
    assert cirros["kernel_path"] == "/boot/vmlinuz"
    assert cirros["initrd_path"] == "/boot/initrd.img"
    assert "console=ttyS0 root=/dev/vda1" in cirros["cmdline"]
    assert "not boot-tested" in cirros["notes"].lower()


def test_vm_creation_rejects_unknown_image():
    client = TestClient(main.app)
    res = client.post("/vms", headers=AUTH, json={
        "name": "vm-test-unknown",
        "vcpus": 1,
        "memory_mb": 512,
        "disk_gb": 4,
        "image": "unknown-nonexistent-os"
    })
    assert res.status_code == 422
    assert "unknown image" in res.json()["detail"]


def test_vm_creation_accepts_catalog_image(monkeypatch):
    client = TestClient(main.app)

    # Mock WorkerClient create_vm to avoid requiring real running node
    fake_worker_vm = {
        "id": "vm-worker123",
        "name": "vm-alpine-test",
        "status": "RUNNING",
        "vcpus": 1,
        "memory_mb": 512,
        "disk_gb": 4,
        "ip_address": "192.168.100.50",
    }
    monkeypatch.setattr(WorkerClient, "create_vm", lambda self, *args, **kwargs: fake_worker_vm)

    res = client.post("/vms", headers=AUTH, json={
        "name": "vm-alpine-test",
        "vcpus": 1,
        "memory_mb": 512,
        "disk_gb": 4,
        "image": "alpine-3-20"
    })
    assert res.status_code == 201
    vm = res.json()
    assert vm["image"] == "alpine-3-20"
    assert vm["name"] == "vm-alpine-test"


def test_image_delete_protection_in_use(monkeypatch):
    client = TestClient(main.app)

    # Create a VM using cirros-0-6-2
    fake_worker_vm = {
        "id": "vm-worker456",
        "name": "vm-cirros-active",
        "status": "RUNNING",
        "vcpus": 1,
        "memory_mb": 256,
        "disk_gb": 2,
        "ip_address": "192.168.100.51",
    }
    monkeypatch.setattr(WorkerClient, "create_vm", lambda self, *args, **kwargs: fake_worker_vm)

    res = client.post("/vms", headers=AUTH, json={
        "name": "vm-cirros-active",
        "vcpus": 1,
        "memory_mb": 256,
        "disk_gb": 2,
        "image": "cirros-0-6-2"
    })
    assert res.status_code == 201

    # Attempt to delete the image while in use
    del_res = client.delete("/images/cirros-0-6-2", headers=AUTH)
    assert del_res.status_code == 409
    assert "in use" in del_res.json()["detail"].lower()


def test_image_delete_not_found():
    client = TestClient(main.app)
    res = client.delete("/images/nonexistent-image-id", headers=AUTH)
    assert res.status_code == 404


def test_image_delete_unreferenced_success():
    client = TestClient(main.app)
    test_db = os.environ["PS023_DB"]

    # Register temporary image
    db.upsert_image("temp-test-image", "Temp Image", "Temp", version="1.0", path=test_db)
    assert db.get_image("temp-test-image", path=test_db) is not None

    # Delete unreferenced image
    res = client.delete("/images/temp-test-image", headers=AUTH)
    assert res.status_code == 204
    assert db.get_image("temp-test-image", path=test_db) is None
