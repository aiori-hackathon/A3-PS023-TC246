import os
import pytest


@pytest.fixture(autouse=True)
def disable_real_cgroups(monkeypatch):
    """Ensure pytest test runs never touch the real /sys/fs/cgroup tree.
    Only test_cgroups.py overrides this against an isolated tmp_path."""
    if "PS023_CGROUP_ROOT" not in os.environ:
        monkeypatch.setenv("PS023_CGROUPS", "off")
