"""Tests for Prometheus GET /metrics endpoint."""
import os
import pytest
from fastapi.testclient import TestClient

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN

import database as db
import main
import metrics as prom_metrics

AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "controller.db")
    monkeypatch.setenv("PS023_DB", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db(test_db)

    # Seed nodes
    db.upsert_node("node-a", "http://127.0.0.1:8001", path=test_db)
    db.update_node("node-a", path=test_db, status="HEALTHY", memory_total_mb=8192,
                   memory_schedulable_mb=6144, cpu_total=4,
                   last_heartbeat=1700000000.0, vms_running=1)

    db.upsert_node("node-b", "http://127.0.0.1:8002", path=test_db)
    db.update_node("node-b", path=test_db, status="UNHEALTHY", memory_total_mb=4096,
                   memory_schedulable_mb=0, cpu_total=2,
                   last_heartbeat=1699990000.0, vms_running=0)


def test_metrics_auth_required():
    client = TestClient(main.app)
    # Missing auth
    res = client.get("/metrics")
    assert res.status_code == 401
    assert "detail" in res.json()

    # Invalid token
    res = client.get("/metrics", headers={"Authorization": "Bearer invalid-token"})
    assert res.status_code == 401


def test_metrics_prometheus_format_valid():
    client = TestClient(main.app)
    res = client.get("/metrics", headers=AUTH)
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    body = res.text

    # Verify standard metric families and documentation
    assert "# HELP ps023_nodes_total" in body
    assert "# TYPE ps023_nodes_total gauge" in body
    assert "ps023_nodes_total 2" in body

    assert "# HELP ps023_nodes_healthy" in body
    assert "ps023_nodes_healthy 1" in body

    assert 'ps023_node_up{node="node-a"} 1' in body
    assert 'ps023_node_up{node="node-b"} 0' in body

    assert 'ps023_node_healthy{node="node-a"} 1' in body
    assert 'ps023_node_healthy{node="node-b"} 0' in body

    assert 'ps023_node_memory_schedulable_mb{node="node-a"} 6144' in body
    assert 'ps023_node_memory_reserved_mb{node="node-a"} 2048' in body
    assert 'ps023_node_cpu_cores{node="node-a"} 4' in body


def test_metrics_decisions_and_refusals():
    client = TestClient(main.app)
    # Record decisions
    from scheduler import Decision
    d1 = Decision(requested_mb=512, selected="node-a", reason="placed on node-a", candidates=[])
    db.record_decision(d1, "vm-11111111")

    d2 = Decision(requested_mb=16384, selected=None, reason="no node accepted: not enough memory", candidates=[])
    db.record_decision(d2, None)

    res = client.get("/metrics", headers=AUTH)
    assert res.status_code == 200
    body = res.text

    assert "ps023_decisions_total 2" in body
    assert "ps023_decision_refusals_total 1" in body


def test_metrics_evacuations_and_recovery():
    client = TestClient(main.app)
    # Add VM with recovery time
    vm_id = db.add_vm("ha-vm", "node-a", 1, 512, 4, "RUNNING", ha=True)
    db.update_vm(vm_id, recovery_time_s=0.45)
    db.add_tombstone("node-b", "w-123", "ha-vm")

    res = client.get("/metrics", headers=AUTH)
    assert res.status_code == 200
    body = res.text

    assert "ps023_evacuations_total 1" in body
    assert "ps023_last_recovery_time_seconds 0.450" in body
    assert 'ps023_vms_total{ha="true",node="node-a",status="RUNNING"} 1' in body


def test_metrics_resilient_to_unreachable_node_and_empty_db(tmp_path, monkeypatch):
    empty_db = str(tmp_path / "empty.db")
    db.init_db(empty_db)
    monkeypatch.setattr(db, "DB_PATH", empty_db)

    # Calling generator directly on empty DB
    raw = prom_metrics.generate_prometheus_metrics(path=empty_db)
    assert "ps023_nodes_total 0" in raw
    assert "ps023_nodes_healthy 0" in raw
    assert "ps023_decisions_total 0" in raw
    assert "ps023_decision_refusals_total 0" in raw
    assert "ps023_evacuations_total 0" in raw
    assert "ps023_last_recovery_time_seconds 0.000" in raw

    # End-to-end via client
    client = TestClient(main.app)
    res = client.get("/metrics", headers=AUTH)
    assert res.status_code == 200
    assert "ps023_nodes_total 0" in res.text
