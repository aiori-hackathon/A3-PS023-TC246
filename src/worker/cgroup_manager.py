"""Cgroups v2 resource limit enforcement for Cloud Hypervisor VMMs.

Implements least-privileged delegated cgroup management:
1. Resolves worker cgroup from /proc/self/cgroup or PS023_CGROUP_ROOT.
2. Tries the worker's own cgroup first (moves worker to child 'worker', enables
   controllers, verifies read-back). If that fails (e.g., terminal-started worker
   shares a scope with other processes), falls back to the parent cgroup.
3. Reads back cgroup.subtree_control and individual limit files (memory.max, cpu.max,
   pids.max); never reports limits or cgroups:true unless verified.
4. Removes empty cgroup directories if attachment fails.
5. Cleans up empty leftover cgroups periodically; preserves live processes.
"""
import errno
import logging
import os
from pathlib import Path
import time

logger = logging.getLogger("cgroups")

# Configurable defaults (Note: defaults of 128 MB overhead, 256 min pids,
# and 1.25 CPU headroom are unmeasured estimates until profiled under load)
DEFAULT_MEMORY_OVERHEAD_MB = 128
DEFAULT_PIDS_MIN = 256
DEFAULT_CPU_HEADROOM = 1.25


class CgroupManager:
    def __init__(self, root=None):
        self.root = root or os.environ.get("PS023_CGROUP_ROOT")
        self.memory_overhead_mb = int(os.environ.get("PS023_CGROUP_MEMORY_OVERHEAD_MB", DEFAULT_MEMORY_OVERHEAD_MB))
        self.pids_min = int(os.environ.get("PS023_CGROUP_PIDS_MIN", DEFAULT_PIDS_MIN))
        self.cpu_headroom = float(os.environ.get("PS023_CGROUP_CPU_HEADROOM", DEFAULT_CPU_HEADROOM))

        self.base_dir = None
        self.enabled = False

        cgroups_toggle = os.environ.get("PS023_CGROUPS", "on").lower()
        if cgroups_toggle in ("off", "0", "false", "no"):
            self.enabled = False
            return

        self._init_cgroups()

    def _init_cgroups(self):
        own_cg = self._resolve_own_cgroup()
        if not own_cg or not own_cg.exists():
            logger.warning("Cgroup root not found; cgroups disabled")
            return

        # If running inside a systemd delegated subgroup (e.g. DelegateSubgroup=service),
        # use parent unit cgroup so the service subgroup remains a leaf for clean systemd restarts.
        parent_cg = own_cg.parent
        if parent_cg and parent_cg != own_cg and parent_cg.name.endswith(".service"):
            if self._try_setup_cgroup_dir(parent_cg, move_worker=False):
                self.base_dir = parent_cg
                self.enabled = True
                self.cleanup_empty_leftovers(min_age_seconds=0.0)
                return

        # Strategy 1: Try worker's own cgroup (move worker to child 'worker', enable controllers)
        if self._try_setup_cgroup_dir(own_cg, move_worker=True):
            self.base_dir = own_cg
            self.enabled = True
            self.cleanup_empty_leftovers(min_age_seconds=0.0)
            return

        # Strategy 2: Fall back to parent cgroup (handles terminal/shared scope)
        parent_cg = own_cg.parent
        if parent_cg and parent_cg.exists() and parent_cg != own_cg:
            logger.info(f"Worker scope {own_cg} cannot delegate controllers; trying parent {parent_cg}")
            if self._try_setup_cgroup_dir(parent_cg, move_worker=False):
                self.base_dir = parent_cg
                self.enabled = True
                self.cleanup_empty_leftovers(min_age_seconds=0.0)
                return

        logger.warning(
            "Could not enable cpu, memory, and pids in cgroup.subtree_control on own or parent cgroup. "
            "Disabling cgroups enforcement."
        )

    def _resolve_own_cgroup(self):
        if self.root:
            p = Path(self.root)
            p.mkdir(parents=True, exist_ok=True)
            return p

        try:
            cgroup_file = Path("/proc/self/cgroup")
            if not cgroup_file.exists():
                return None
            for line in cgroup_file.read_text().splitlines():
                parts = line.strip().split(":")
                if len(parts) == 3:
                    subpath = parts[2].lstrip("/")
                    cg_path = Path("/sys/fs/cgroup") / subpath
                    if cg_path.exists():
                        return cg_path
            return Path("/sys/fs/cgroup")
        except Exception as e:
            logger.warning(f"Could not resolve /proc/self/cgroup: {e}")
            return None

    def _try_setup_cgroup_dir(self, cg_dir, move_worker=True):
        """Attempts to enable cpu, memory, pids in subtree_control and confirms by reading back."""
        try:
            controllers_file = cg_dir / "cgroup.controllers"
            subtree_file = cg_dir / "cgroup.subtree_control"
            if not controllers_file.exists() or not subtree_file.exists():
                return False

            available = set(controllers_file.read_text().split())
            needed = {"cpu", "memory", "pids"}
            if not needed.issubset(available):
                return False

            if move_worker:
                # Worker moves into its own child cgroup so parent has no internal processes
                worker_cg = cg_dir / "worker"
                worker_cg.mkdir(exist_ok=True)
                (worker_cg / "cgroup.procs").write_text(str(os.getpid()))

            # Request needed controllers
            current_sub = set(subtree_file.read_text().split())
            to_enable = needed - current_sub
            if to_enable:
                enable_str = " ".join(f"+{c}" for c in to_enable)
                subtree_file.write_text(enable_str)

            # Verification requirement: MUST confirm by reading back
            verified_sub = {c.lstrip("+") for c in subtree_file.read_text().split()}
            return needed.issubset(verified_sub)
        except Exception as e:
            logger.debug(f"Setup on {cg_dir} failed: {e}")
            return False

    def cleanup_empty_leftovers(self, min_age_seconds=10.0):
        """Removes empty leftover VM cgroups; skips cgroups younger than min_age_seconds."""
        if not self.base_dir or not self.base_dir.exists():
            return
        now = time.time()
        try:
            for child in self.base_dir.glob("ps023-vmm-*"):
                if not child.is_dir():
                    continue
                try:
                    # Fix race: skip cgroups younger than min_age_seconds
                    if (now - child.stat().st_mtime) < min_age_seconds:
                        continue
                    procs_file = child / "cgroup.procs"
                    if procs_file.exists():
                        pids = [p for p in procs_file.read_text().split() if p.strip()]
                        if not pids:
                            try:
                                child.rmdir()
                            except OSError as e:
                                if e.errno == errno.ENOTEMPTY:
                                    for f in child.iterdir():
                                        if f.is_file():
                                            f.unlink(missing_ok=True)
                                    child.rmdir()
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"Error during leftover cgroup cleanup: {e}")

    def vm_cgroup_dir(self, vm_id):
        if not self.base_dir:
            return None
        return self.base_dir / f"ps023-vmm-{vm_id}"

    def create_vm_cgroup(self, vm_id, vcpus, memory_mb):
        """Create and configure limits for a VM cgroup with verified read-back."""
        if not self.enabled or not self.base_dir:
            return {"enabled": False, "limits": None, "path": None}

        cg_dir = self.vm_cgroup_dir(vm_id)
        try:
            cg_dir.mkdir(exist_ok=True)

            # 1. Memory limit (guest memory + overhead)
            overhead_bytes = self.memory_overhead_mb * 1024 * 1024
            mem_limit_bytes = (memory_mb * 1024 * 1024) + overhead_bytes
            mem_file = cg_dir / "memory.max"
            mem_file.write_text(str(mem_limit_bytes))
            read_mem = int(mem_file.read_text().strip())

            # 2. CPU quota
            period = 100000
            quota = int(vcpus * period * self.cpu_headroom)
            cpu_file = cg_dir / "cpu.max"
            cpu_file.write_text(f"{quota} {period}")
            read_cpu_parts = cpu_file.read_text().strip().split()
            read_quota = int(read_cpu_parts[0])
            read_period = int(read_cpu_parts[1])

            # 3. PIDs limit
            pids_limit = max(self.pids_min, vcpus * 16)
            pids_file = cg_dir / "pids.max"
            pids_file.write_text(str(pids_limit))
            read_pids = int(pids_file.read_text().strip())

            # Verified limits
            limits = {
                "memory_max_bytes": read_mem,
                "memory_overhead_mb": self.memory_overhead_mb,
                "cpu_quota": read_quota,
                "cpu_period": read_period,
                "cpu_headroom": self.cpu_headroom,
                "pids_max": read_pids,
            }
            return {"enabled": True, "limits": limits, "path": str(cg_dir)}
        except Exception as e:
            logger.warning(f"Failed to configure cgroup for {vm_id}: {e}. Falling back.")
            try:
                if cg_dir.exists():
                    cg_dir.rmdir()
            except OSError:
                pass
            return {"enabled": False, "limits": None, "path": None}

    def attach_vmm(self, vm_id, pid):
        """Write VMM process PID to cgroup.procs. If write fails, removes empty cgroup directory."""
        if not self.enabled or not self.base_dir:
            return False
        cg_dir = self.vm_cgroup_dir(vm_id)
        if not cg_dir or not cg_dir.exists():
            return False
        try:
            procs_file = cg_dir / "cgroup.procs"
            procs_file.write_text(str(pid))
            attached = [p for p in procs_file.read_text().split() if p.strip()]
            if str(pid) not in attached:
                raise RuntimeError(f"PID {pid} not found in {procs_file} after write")
            return True
        except Exception as e:
            logger.warning(f"Failed to attach PID {pid} to cgroup {cg_dir}: {e}. Removing empty cgroup.")
            self.remove_vm_cgroup(vm_id)
            return False

    def remove_vm_cgroup(self, vm_id):
        """Remove cgroup directory after VMM is reaped. Tolerates ENOENT and EBUSY with retries."""
        if not self.base_dir:
            return
        cg_dir = self.vm_cgroup_dir(vm_id)
        if not cg_dir or not cg_dir.exists():
            return

        for attempt in range(4):
            try:
                cg_dir.rmdir()
                return
            except FileNotFoundError:
                return
            except OSError as e:
                if e.errno == errno.ENOTEMPTY:
                    # On mock filesystems (tests), regular files remain in the directory.
                    for f in cg_dir.iterdir():
                        if f.is_file():
                            f.unlink(missing_ok=True)
                    try:
                        cg_dir.rmdir()
                        return
                    except OSError:
                        pass
                elif e.errno == errno.EBUSY:
                    if attempt < 3:
                        time.sleep(0.1)
                        continue
                    logger.warning(f"cgroup {cg_dir} busy after 4 attempts, skipping rmdir")
                elif e.errno == errno.ENOENT:
                    return
                else:
                    logger.warning(f"Could not remove cgroup {cg_dir}: {e}")
                    return
