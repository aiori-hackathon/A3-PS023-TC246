import json
import os
import shutil
import signal
import subprocess
import sys
import time

import psutil
import pytest

import vm_manager as vmm

VM = "vm-aaaaaaaa"
SPAWNED = []


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(vmm, "VM_ROOT", tmp_path)
    orig = vmm.VMManager._wait_exit  # keep the real logic, cap the waits
    monkeypatch.setattr(
        vmm.VMManager, "_wait_exit",
        lambda self, vm_id, timeout: orig(self, vm_id, min(timeout, 1)))
    yield vmm.VMManager()
    for p in SPAWNED:  # never leave test processes behind
        if p.poll() is None:
            p.kill()
        p.wait()
    SPAWNED.clear()


def write_meta(vm_id, slot=0):
    d = vmm.VM_ROOT / vm_id
    d.mkdir(exist_ok=True)
    (d / "meta.json").write_text(json.dumps({"id": vm_id, "slot": slot}))
    return d


def spawn(mgr, vm_id, ignore_term=False):
    """A stand-in VMM: a sleeping process with the socket path on its cmdline."""
    d = write_meta(vm_id)
    code = "import signal, time\n"
    if ignore_term:
        code += "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    code += "time.sleep(300)"
    proc = subprocess.Popen([sys.executable, "-c", code, str(d / "vm.sock")],
                            start_new_session=True)
    SPAWNED.append(proc)
    (d / "vmm.pid").write_text(str(proc.pid))
    mgr._procs[vm_id] = proc
    time.sleep(0.5)  # let the signal handler install
    return proc


class FakeCH:
    def __init__(self, proc, obeys=False):
        self.proc, self.obeys, self.calls = proc, obeys, []

    def power_button(self):
        self.calls.append("power_button")
        if self.obeys:
            self.proc.terminate()

    def shutdown(self):
        self.calls.append("shutdown")

    def vmm_shutdown(self):
        self.calls.append("vmm_shutdown")

    def state(self):
        return "Running"


def test_graceful_stop(mgr, monkeypatch):
    proc = spawn(mgr, VM)
    fake = FakeCH(proc, obeys=True)
    monkeypatch.setattr(mgr, "_ch", lambda vm_id: fake)
    assert mgr.stop(VM) == "graceful"
    assert fake.calls == ["power_button"]
    assert proc.returncode is not None
    assert VM not in mgr._procs
    assert not (vmm.VM_ROOT / VM / "vmm.pid").exists()


def test_power_button_ignored_then_sigterm(mgr, monkeypatch):
    proc = spawn(mgr, VM)
    fake = FakeCH(proc)
    monkeypatch.setattr(mgr, "_ch", lambda vm_id: fake)
    assert mgr.stop(VM, graceful_timeout=1) == "sigterm"
    assert fake.calls == ["power_button", "shutdown", "vmm_shutdown"]
    assert proc.returncode == -signal.SIGTERM


def test_frozen_vmm_is_killed_and_reaped(mgr, monkeypatch):
    proc = spawn(mgr, VM, ignore_term=True)
    fake = FakeCH(proc)
    monkeypatch.setattr(mgr, "_ch", lambda vm_id: fake)
    assert mgr.stop(VM, graceful_timeout=1) == "sigkill"
    assert proc.returncode == -signal.SIGKILL
    assert not psutil.pid_exists(proc.pid)  # reaped: no zombie left
    assert VM not in mgr._procs


def test_stop_when_nothing_runs(mgr):
    write_meta(VM)
    assert mgr.stop(VM) == "already-stopped"


def test_stop_unknown_vm(mgr):
    with pytest.raises(vmm.VMError):
        mgr.stop("vm-ffffffff")


def test_foreign_pid_is_not_our_vmm(mgr):
    d = write_meta(VM)
    (d / "vmm.pid").write_text(str(os.getpid()))  # a live pid, not our VMM
    assert mgr._alive(VM) is False


def test_status_stopped_without_vmm(mgr):
    write_meta(VM)
    assert mgr.status(VM) == "stopped"


def test_delete_stops_vmm_and_removes_files(mgr, monkeypatch):
    proc = spawn(mgr, VM)
    fake = FakeCH(proc, obeys=True)
    monkeypatch.setattr(mgr, "_ch", lambda vm_id: fake)
    mgr.delete(VM)
    assert not (vmm.VM_ROOT / VM).exists()
    assert proc.returncode is not None


def test_slot_exhaustion_and_reuse(mgr, monkeypatch):
    monkeypatch.setattr(vmm, "SLOT_START", 0)
    monkeypatch.setattr(vmm, "SLOT_COUNT", 2)
    write_meta("vm-aaaaaaaa", 0)
    write_meta("vm-bbbbbbbb", 1)
    with pytest.raises(vmm.VMError):
        mgr._free_slot()
    shutil.rmtree(vmm.VM_ROOT / "vm-aaaaaaaa")
    assert mgr._free_slot() == 0
