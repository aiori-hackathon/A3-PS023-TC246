"""Unit tests for cgroups v2 resource limit enforcement."""
import errno
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import vm_manager
from cgroup_manager import (
    CgroupManager,
    DEFAULT_CPU_HEADROOM,
    DEFAULT_MEMORY_OVERHEAD_MB,
    DEFAULT_PIDS_MIN,
)


def _setup_fake_cgroup(cg_dir, controllers="cpu memory pids"):
    cg_dir.mkdir(parents=True, exist_ok=True)
    (cg_dir / "cgroup.controllers").write_text(controllers)
    (cg_dir / "cgroup.subtree_control").write_text("")
    (cg_dir / "cgroup.procs").write_text("1001\n")


def test_verified_limits_read_back(tmp_path, monkeypatch):
    """Limits are calculated and strictly verified by reading back."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.setenv("PS023_CGROUP_ROOT", str(tmp_path))
    _setup_fake_cgroup(tmp_path)

    mgr = CgroupManager()
    assert mgr.enabled is True
    assert mgr.base_dir == tmp_path

    vcpus = 2
    mem_mb = 1024
    res = mgr.create_vm_cgroup("vm-abc12345", vcpus, mem_mb)
    assert res["enabled"] is True
    assert res["limits"] is not None

    expected_mem = (mem_mb + DEFAULT_MEMORY_OVERHEAD_MB) * 1024 * 1024
    expected_quota = int(vcpus * 100000 * DEFAULT_CPU_HEADROOM)
    expected_pids = max(DEFAULT_PIDS_MIN, vcpus * 16)

    assert res["limits"]["memory_max_bytes"] == expected_mem
    assert res["limits"]["cpu_quota"] == expected_quota
    assert res["limits"]["cpu_period"] == 100000
    assert res["limits"]["pids_max"] == expected_pids

    # Confirm files on disk match verified values
    vm_dir = tmp_path / "ps023-vmm-vm-abc12345"
    assert int((vm_dir / "memory.max").read_text().strip()) == expected_mem
    assert (vm_dir / "cpu.max").read_text().strip() == f"{expected_quota} 100000"
    assert int((vm_dir / "pids.max").read_text().strip()) == expected_pids


def test_controller_enable_failure_disables_cgroups(tmp_path, monkeypatch):
    """If required controllers are missing or cannot be verified in subtree_control, cgroups is disabled."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.setenv("PS023_CGROUP_ROOT", str(tmp_path))
    # Missing 'pids' controller
    _setup_fake_cgroup(tmp_path, controllers="cpu memory")

    mgr = CgroupManager()
    assert mgr.enabled is False
    res = mgr.create_vm_cgroup("vm-test0001", 1, 512)
    assert res["enabled"] is False
    assert res["limits"] is None
    assert res["path"] is None


def test_fallback_from_own_cgroup_to_parent(tmp_path, monkeypatch):
    """When the worker's own scope cannot delegate, it falls back to the parent cgroup."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.delenv("PS023_CGROUP_ROOT", raising=False)

    parent_cg = tmp_path / "parent_scope"
    own_cg = parent_cg / "terminal_session.scope"
    _setup_fake_cgroup(parent_cg, controllers="cpu memory pids")
    # own_cg has no controllers available
    _setup_fake_cgroup(own_cg, controllers="")

    with patch.object(CgroupManager, "_resolve_own_cgroup", return_value=own_cg):
        mgr = CgroupManager()
        assert mgr.enabled is True
        assert mgr.base_dir == parent_cg


def test_attach_failure_cleans_empty_cgroup(tmp_path, monkeypatch):
    """If attaching the VMM PID fails, the empty cgroup directory is promptly removed."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.setenv("PS023_CGROUP_ROOT", str(tmp_path))
    _setup_fake_cgroup(tmp_path)

    mgr = CgroupManager()
    cg_res = mgr.create_vm_cgroup("vm-failattach", 1, 512)
    vm_dir = Path(cg_res["path"])
    assert vm_dir.exists()

    orig_write = Path.write_text

    def mock_write(path_obj, content, *args, **kwargs):
        if path_obj.name == "cgroup.procs":
            raise OSError("Permission denied")
        return orig_write(path_obj, content, *args, **kwargs)

    with patch.object(Path, "write_text", mock_write):
        attached = mgr.attach_vmm("vm-failattach", 99999)
        assert attached is False
        assert not vm_dir.exists()


def test_cleanup_empty_leftovers_race_and_active_pids(tmp_path, monkeypatch):
    """Cleanup skips young cgroups (< 10s), deletes empty older cgroups, and preserves live cgroups."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.setenv("PS023_CGROUP_ROOT", str(tmp_path))
    _setup_fake_cgroup(tmp_path)

    mgr = CgroupManager()

    # 1. Young empty cgroup (< 10s old)
    young_dir = tmp_path / "ps023-vmm-young"
    young_dir.mkdir()
    (young_dir / "cgroup.procs").write_text("")

    # 2. Old empty cgroup (> 10s old)
    old_empty_dir = tmp_path / "ps023-vmm-oldempty"
    old_empty_dir.mkdir()
    (old_empty_dir / "cgroup.procs").write_text("")
    old_time = time.time() - 25.0
    os.utime(old_empty_dir, (old_time, old_time))

    # 3. Old cgroup with live processes (> 10s old, but has PID)
    old_active_dir = tmp_path / "ps023-vmm-oldactive"
    old_active_dir.mkdir()
    (old_active_dir / "cgroup.procs").write_text("54321\n")
    os.utime(old_active_dir, (old_time, old_time))

    mgr.cleanup_empty_leftovers(min_age_seconds=10.0)

    # Young is preserved (avoids race with in-flight create)
    assert young_dir.exists()
    # Old active is preserved
    assert old_active_dir.exists()
    # Old empty is removed
    assert not old_empty_dir.exists()


def test_remove_vm_cgroup_ebusy_retry_and_enoent(tmp_path, monkeypatch):
    """Tolerates ENOENT and retries EBUSY before giving up."""
    monkeypatch.setenv("PS023_CGROUPS", "on")
    monkeypatch.setenv("PS023_CGROUP_ROOT", str(tmp_path))
    _setup_fake_cgroup(tmp_path)

    mgr = CgroupManager()
    vm_dir = tmp_path / "ps023-vmm-busy"
    vm_dir.mkdir()

    # Case 1: EBUSY twice, then succeeds
    calls = 0
    orig_rmdir = Path.rmdir

    def mock_rmdir(self):
        nonlocal calls
        if self == vm_dir:
            calls += 1
            if calls < 3:
                raise OSError(errno.EBUSY, "Device or resource busy")
        return orig_rmdir(self)

    with patch.object(Path, "rmdir", mock_rmdir):
        mgr.remove_vm_cgroup("busy")
        assert calls == 3
        assert not vm_dir.exists()

    # Case 2: Already gone (ENOENT)
    mgr.remove_vm_cgroup("already-gone-vm")  # Should not raise


def test_existing_running_vms_default_to_cgroups_false(tmp_path, monkeypatch):
    """Existing VMs without cgroup metadata return cgroups: false and cgroup_limits: None."""
    vms_dir = tmp_path / "vms"
    monkeypatch.setattr(vm_manager, "VM_ROOT", vms_dir)
    monkeypatch.setenv("PS023_CGROUPS", "off")

    vm_dir = vms_dir / "vm-old00001"
    vm_dir.mkdir(parents=True)
    meta = {
        "id": "vm-old00001",
        "name": "legacy-vm",
        "vcpus": 1,
        "memory_mb": 512,
        "disk_gb": 4,
        "slot": 0,
        "tap": "tapvm0",
        "mac": "12:34:56:78:90:00",
        "ip": "192.168.100.10",
        "created_at": time.time(),
    }
    (vm_dir / "meta.json").write_text(json.dumps(meta))

    vmm = vm_manager.VMManager()
    with patch.object(vmm, "status", return_value="stopped"):
        fetched = vmm.get("vm-old00001")
        assert fetched["cgroups"] is False
        assert fetched["cgroup_limits"] is None
