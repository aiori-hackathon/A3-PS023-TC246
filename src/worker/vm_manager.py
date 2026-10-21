"""VM lifecycle for one worker: per-VM files, VMM processes, cleanup."""
import json
import os
import shutil
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

import psutil

from cloud_hypervisor import CloudHypervisor

LAB = Path.home() / "ps023" / "lab"
VM_ROOT = Path(os.environ.get("PS023_VM_ROOT", str(Path.home() / "ps023" / "vms")))
BASE_IMAGE = Path(os.environ.get("PS023_BASE_IMAGE", str(LAB / "images" / "ubuntu-noble.raw")))
KERNEL = Path(os.environ.get("PS023_KERNEL", str(LAB / "kernel" / "vmlinux.bin")))
CH_BIN = "cloud-hypervisor"
CMDLINE = "console=ttyS0 root=/dev/vda1 rw"
SUBNET = os.environ.get("PS023_SUBNET", "192.168.100")
GATEWAY = f"{SUBNET}.1"
SLOT_START = int(os.environ.get("PS023_SLOT_START", "0"))
SLOT_COUNT = int(os.environ.get("PS023_SLOT_COUNT", "8"))
GIB = 1024 ** 3


class VMError(Exception):
    pass


class VMManager:
    def __init__(self):
        VM_ROOT.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._procs = {}  # vm_id -> Popen, so exited children get reaped
        self._unreaped = []  # exited VMMs we could not collect yet

    # ---------- paths and metadata ----------
    def _dir(self, vm_id):
        return VM_ROOT / vm_id

    def _sock(self, vm_id):
        return self._dir(vm_id) / "vm.sock"

    def _meta(self, vm_id):
        try:
            return json.loads((self._dir(vm_id) / "meta.json").read_text())
        except FileNotFoundError:
            raise VMError(f"unknown vm {vm_id}")

    def _ids(self):
        return sorted(p.parent.name for p in VM_ROOT.glob("*/meta.json"))

    def _ch(self, vm_id):
        return CloudHypervisor(str(self._sock(vm_id)))

    # ---------- create ----------
    def _free_slot(self):
        used = {self._meta(i)["slot"] for i in self._ids()}
        for s in range(SLOT_START, SLOT_START + SLOT_COUNT):
            if s not in used:
                return s
        raise VMError("no free slot (all TAP/IP slots are in use)")

    def create(self, name, vcpus, memory_mb, disk_gb=4):
        if vcpus < 1 or memory_mb < 128 or disk_gb < 1:
            raise VMError("invalid resources")
        if not BASE_IMAGE.exists():
            raise VMError(f"base image missing: {BASE_IMAGE}")
        if not KERNEL.exists():
            raise VMError(f"kernel missing: {KERNEL}")
        with self._lock:
            slot = self._free_slot()
            tap = f"tapvm{slot}"
            if not Path(f"/sys/class/net/{tap}").exists():
                raise VMError(f"{tap} missing: create the TAP pool first")
            vm_id = "vm-" + uuid.uuid4().hex[:8]
            d = self._dir(vm_id)
            d.mkdir(parents=True)
            meta = {
                "id": vm_id, "name": name, "vcpus": vcpus,
                "memory_mb": memory_mb, "disk_gb": disk_gb, "slot": slot,
                "tap": tap, "mac": f"12:34:56:78:90:{slot:02x}",
                "ip": f"{SUBNET}.{10 + slot}", "created_at": time.time(),
            }
            try:
                subprocess.run(["cp", "--reflink=auto", str(BASE_IMAGE),
                                str(d / "disk.raw")], check=True)
                if disk_gb * GIB > (d / "disk.raw").stat().st_size:
                    os.truncate(d / "disk.raw", disk_gb * GIB)
                self._make_seed(d, meta)
                (d / "meta.json").write_text(json.dumps(meta, indent=2))
            except Exception:
                shutil.rmtree(d, ignore_errors=True)
                raise
            return meta

    def _make_seed(self, d, meta):
        password = os.environ.get("PS023_VM_PASSWORD")
        if not password:
            raise VMError("PS023_VM_PASSWORD is not set")
        user_data = "\n".join([
            "#cloud-config",
            f"hostname: {meta['name']}",
            "users:",
            "  - name: rajyavardhan",
            "    groups: [sudo]",
            "    shell: /bin/bash",
            "    sudo: ALL=(ALL) NOPASSWD:ALL",
            "    lock_passwd: false",
            f"    plain_text_passwd: {json.dumps(password)}",
            "ssh_pwauth: true",
            "chpasswd:",
            "  expire: false",
            "",
        ])
        meta_data = f"instance-id: {meta['id']}\nlocal-hostname: {meta['name']}\n"
        network = "\n".join([
            "version: 2",
            "ethernets:",
            "  nic0:",
            "    match:",
            f"      macaddress: \"{meta['mac']}\"",
            "    set-name: ens3",
            f"    addresses: [{meta['ip']}/24]",
            "    routes:",
            "      - to: default",
            f"        via: {GATEWAY}",
            "    nameservers:",
            "      addresses: [1.1.1.1, 8.8.8.8]",
            "",
        ])
        seed = d / "seed.img"
        with open(seed, "wb") as f:
            f.truncate(2 * 1024 * 1024)
        subprocess.run(["mkfs.vfat", "-n", "CIDATA", str(seed)],
                       check=True, capture_output=True)
        for fname, text in (("user-data", user_data),
                            ("meta-data", meta_data),
                            ("network-config", network)):
            (d / fname).write_text(text)
            subprocess.run(["mcopy", "-i", str(seed), str(d / fname),
                            f"::/{fname}"], check=True, capture_output=True)

    # ---------- process tracking ----------
    def _alive(self, vm_id):
        try:
            pid = int((self._dir(vm_id) / "vmm.pid").read_text())
            p = psutil.Process(pid)
            if p.status() == psutil.STATUS_ZOMBIE:
                proc = self._procs.get(vm_id)
                if proc:
                    proc.poll()  # reap it
                return False
            # guard against pid reuse: it must be OUR vmm for THIS vm
            return str(self._sock(vm_id)) in " ".join(p.cmdline())
        except (FileNotFoundError, ValueError,
                psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _wait_exit(self, vm_id, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if not self._alive(vm_id):
                return True
            time.sleep(0.5)
        return not self._alive(vm_id)

    def _signal(self, vm_id, sig):
        try:
            pid = int((self._dir(vm_id) / "vmm.pid").read_text())
            os.kill(pid, sig)
        except (FileNotFoundError, ValueError, ProcessLookupError):
            pass

    def _clean_runtime(self, vm_id):
        d = self._dir(vm_id)
        for f in ("vm.sock", "vm.sock.lock", "vmm.pid"):
            (d / f).unlink(missing_ok=True)
        proc = self._procs.pop(vm_id, None)
        if proc is not None:
            try:
                proc.wait(timeout=5)  # collect the exit status: no zombie
            except subprocess.TimeoutExpired:
                self._unreaped.append(proc)  # retried from _reap_pending()

    def _reap_pending(self):
        self._unreaped = [p for p in self._unreaped if p.poll() is None]

    # ---------- start ----------
    def _config(self, meta):
        d = self._dir(meta["id"])
        return {
            "cpus": {"boot_vcpus": meta["vcpus"], "max_vcpus": meta["vcpus"]},
            "memory": {"size": meta["memory_mb"] * 1024 * 1024},
            "payload": {"kernel": str(KERNEL), "cmdline": CMDLINE},
            "disks": [
                {"path": str(d / "disk.raw"), "image_type": "Raw"},
                {"path": str(d / "seed.img"), "image_type": "Raw",
                 "readonly": True},
            ],
            "net": [{"tap": meta["tap"], "mac": meta["mac"]}],
            "serial": {"mode": "File", "file": str(d / "serial.log")},
            "console": {"mode": "Off"},
        }

    def start(self, vm_id):
        meta = self._meta(vm_id)
        d = self._dir(vm_id)
        if self._alive(vm_id):
            if self._ch(vm_id).state() == "Running":
                return
            self._kill_hard(vm_id)  # idle or half-started VMM: begin clean
        self._clean_runtime(vm_id)
        log = open(d / "vmm.log", "ab")
        proc = subprocess.Popen(
            [CH_BIN, "--api-socket", f"path={self._sock(vm_id)}"],
            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True,  # the setsid lesson: VMs outlive us
        )
        log.close()
        self._procs[vm_id] = proc
        (d / "vmm.pid").write_text(str(proc.pid))
        try:
            end = time.time() + 5
            while not self._sock(vm_id).exists():
                if proc.poll() is not None or time.time() > end:
                    raise VMError("cloud-hypervisor did not start; see vmm.log")
                time.sleep(0.1)
            ch = self._ch(vm_id)
            ch.create(self._config(meta))
            ch.boot()
        except Exception:
            self._kill_hard(vm_id)
            self._clean_runtime(vm_id)
            raise

    # ---------- stop: graceful first, then escalate ----------
    def stop(self, vm_id, graceful_timeout=30):
        self._meta(vm_id)
        if not self._alive(vm_id):
            self._clean_runtime(vm_id)
            return "already-stopped"
        ch = self._ch(vm_id)
        self._quiet(ch.power_button)
        if self._wait_exit(vm_id, graceful_timeout):
            self._clean_runtime(vm_id)
            return "graceful"
        self._quiet(ch.shutdown)
        self._quiet(ch.vmm_shutdown)
        if self._wait_exit(vm_id, 5):
            self._clean_runtime(vm_id)
            return "forced-api"
        method = self._kill_hard(vm_id)
        self._clean_runtime(vm_id)
        return method

    def _kill_hard(self, vm_id):
        self._signal(vm_id, signal.SIGTERM)
        if self._wait_exit(vm_id, 5):
            return "sigterm"
        self._signal(vm_id, signal.SIGKILL)
        if self._wait_exit(vm_id, 5):
            return "sigkill"
        raise VMError(f"{vm_id}: VMM process will not die")

    @staticmethod
    def _quiet(fn):
        try:
            fn()
        except Exception:
            pass  # best effort: we verify by checking the process itself

    # ---------- delete / read ----------
    def delete(self, vm_id):
        self._meta(vm_id)
        self.stop(vm_id, graceful_timeout=10)
        shutil.rmtree(self._dir(vm_id))

    def status(self, vm_id):
        if not self._alive(vm_id):
            return "stopped"
        s = self._ch(vm_id).state()
        return {"Running": "running", "unreachable": "stopped"}.get(s, s.lower())

    def get(self, vm_id):
        meta = self._meta(vm_id)
        meta["status"] = self.status(vm_id)
        return meta

    def list(self):
        self._reap_pending()
        return [self.get(i) for i in self._ids()]
