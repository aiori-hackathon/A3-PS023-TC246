"""Tests for WorkerClient operation-specific timeouts."""
import pytest
from worker_client import WorkerClient, DEFAULT_STOP_TIMEOUT_S

def test_stop_vm_uses_45s_timeout(monkeypatch):
    calls = []
    
    def fake_req(self, method, path, json=None, timeout=10.0):
        calls.append((method, path, timeout))
        return {"status": "STOPPED"}
    
    monkeypatch.setattr(WorkerClient, "_req", fake_req)
    
    client = WorkerClient("node-a", "http://127.0.0.1:8001", token="test-token-1234567890")
    try:
        assert DEFAULT_STOP_TIMEOUT_S == 45.0
        client.stop_vm("w-vm-12345678")
        assert len(calls) == 1
        assert calls[0] == ("POST", "/vms/w-vm-12345678/stop", 45.0)
        
        # Test other operations retain distinct specific timeouts
        client.health()
        assert calls[1] == ("GET", "/health", 3.0)
        
        client.resources()
        assert calls[2] == ("GET", "/resources", 5.0)
        
        client.delete_vm("w-vm-12345678")
        assert calls[3] == ("DELETE", "/vms/w-vm-12345678", 30.0)
    finally:
        client.close()
