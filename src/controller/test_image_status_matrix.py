"""Unit tests for Step D1 per-node image status logic, kernel invalidation, and matrix evaluation."""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import image_evaluator
import main
import database as db

AUTH = {"Authorization": "Bearer test-token-0123456789abcdef"}


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "controller.db")
    test_matrix = str(tmp_path / "image_boot_matrix.json")
    fake_kernel = tmp_path / "vmlinux.bin"
    fake_kernel.write_bytes(b"mock-kernel-binary-content-v1")

    monkeypatch.setenv("PS023_DB", test_db)
    monkeypatch.setenv("PS023_BOOT_MATRIX", test_matrix)
    monkeypatch.setenv("PS023_KERNEL", str(fake_kernel))
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db(test_db)

    return {
        "db": test_db,
        "matrix": test_matrix,
        "kernel": fake_kernel,
        "tmp_path": tmp_path,
    }


def test_status_missing_file(mock_env):
    """When the image file does not exist, per-node status must be UNAVAILABLE(file missing)."""
    fake_img = {
        "id": "nonexistent-os",
        "path": str(mock_env["tmp_path"] / "nonexistent.raw"),
    }
    statuses = image_evaluator.evaluate_image_node_status(fake_img)
    assert statuses["node-a"] == "UNAVAILABLE(file missing)"
    assert statuses["node-b"] == "UNAVAILABLE(file missing)"

    enriched = image_evaluator.enrich_image_status(fake_img)
    assert enriched["status"] == "UNAVAILABLE"
    assert enriched["badge"] == "A: Unavailable / B: Unavailable"


def test_status_unverified_by_default(mock_env):
    """When image file exists but no matrix record exists, status is NOT_VERIFIED."""
    raw_file = mock_env["tmp_path"] / "test-img.raw"
    raw_file.write_bytes(b"raw-content")

    fake_img = {"id": "test-os", "path": str(raw_file)}
    statuses = image_evaluator.evaluate_image_node_status(fake_img)
    assert statuses["node-a"] == "NOT_VERIFIED"
    assert statuses["node-b"] == "NOT_VERIFIED"

    enriched = image_evaluator.enrich_image_status(fake_img)
    assert enriched["status"] == "NOT_VERIFIED"
    assert enriched["badge"] == "A: Not Verified / B: Not Verified"
    assert enriched["kernel_compat"] == "COMPATIBLE"


def test_status_ready_with_matching_kernel(mock_env):
    """When a PASS record exists matching current kernel sha256, node is READY."""
    raw_file = mock_env["tmp_path"] / "test-img.raw"
    raw_file.write_bytes(b"raw-content")

    current_ksha = image_evaluator.get_kernel_sha256(str(mock_env["kernel"]))

    matrix = [
        {
            "image": "test-os",
            "node": "node-a",
            "kernel_sha256": current_ksha,
            "verdict": "PASS",
            "t_ssh": 12.5,
        }
    ]
    Path(mock_env["matrix"]).write_text(json.dumps(matrix))

    fake_img = {"id": "test-os", "path": str(raw_file)}
    statuses = image_evaluator.evaluate_image_node_status(fake_img)
    assert statuses["node-a"] == "READY"
    assert statuses["node-b"] == "NOT_VERIFIED"

    enriched = image_evaluator.enrich_image_status(fake_img)
    assert enriched["status"] == "READY"
    assert enriched["badge"] == "A: Ready / B: Not Verified"


def test_status_invalidated_when_kernel_changes(mock_env):
    """When kernel changes, previous PASS records are invalidated to NOT_VERIFIED."""
    raw_file = mock_env["tmp_path"] / "test-img.raw"
    raw_file.write_bytes(b"raw-content")

    matrix = [
        {
            "image": "test-os",
            "node": "node-a",
            "kernel_sha256": "old-sha256-kernel-pre-rebuild",
            "verdict": "PASS",
        }
    ]
    Path(mock_env["matrix"]).write_text(json.dumps(matrix))

    fake_img = {"id": "test-os", "path": str(raw_file)}
    statuses = image_evaluator.evaluate_image_node_status(fake_img)
    # Old kernel record must be invalidated!
    assert statuses["node-a"] == "NOT_VERIFIED"
    assert statuses["node-b"] == "NOT_VERIFIED"


def test_status_failed_reason(mock_env):
    """When a FAIL record exists, node is FAILED(reason)."""
    raw_file = mock_env["tmp_path"] / "test-img.raw"
    raw_file.write_bytes(b"raw-content")

    current_ksha = image_evaluator.get_kernel_sha256(str(mock_env["kernel"]))

    matrix = [
        {
            "image": "test-os",
            "node": "node-a",
            "kernel_sha256": current_ksha,
            "verdict": "PASS",
        },
        {
            "image": "test-os",
            "node": "node-b",
            "kernel_sha256": current_ksha,
            "verdict": "FAIL",
            "reason": "cannot mount root filesystem",
        },
    ]
    Path(mock_env["matrix"]).write_text(json.dumps(matrix))

    fake_img = {"id": "test-os", "path": str(raw_file)}
    statuses = image_evaluator.evaluate_image_node_status(fake_img)
    assert statuses["node-a"] == "READY"
    assert statuses["node-b"] == "FAILED(cannot mount root filesystem)"

    enriched = image_evaluator.enrich_image_status(fake_img)
    assert enriched["badge"] == "A: Ready / B: Failed"


def test_api_list_images_returns_node_status_and_badge(mock_env):
    """API endpoint /images enriches each image with node_status and badge."""
    client = TestClient(main.app)
    res = client.get("/images", headers=AUTH)
    assert res.status_code == 200
    images = res.json()
    assert len(images) >= 7

    for img in images:
        assert "node_status" in img
        assert "node-a" in img["node_status"]
        assert "node-b" in img["node_status"]
        assert "badge" in img
        assert img["kernel_compat"] == "COMPATIBLE"
