#!/usr/bin/env python3
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

TOKEN = os.environ.get("PS023_API_TOKEN")
VMPASS = os.environ.get("PS023_VM_PASSWORD")
BASE_URL = "http://127.0.0.1:8000"

if not TOKEN or not VMPASS:
    print("PS023_API_TOKEN or PS023_VM_PASSWORD not set")
    sys.exit(1)


def api(method, path, body=None):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = json.dumps(body).encode() if body else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        content = resp.read().decode()
        return json.loads(content) if content else {}


def check_port_22(ip, timeout=0.2):
    try:
        s = socket.create_connection((ip, 22), timeout=timeout)
        s.close()
        return True
    except (socket.timeout, OSError):
        return False


def run_single(run_idx):
    t0 = time.time()
    vm = api(
        "POST",
        "/vms",
        {
            "name": f"diag-bimod-{run_idx}",
            "vcpus": 1,
            "memory_mb": 512,
            "disk_gb": 4,
            "target_node": "node-a",
        },
    )
    t_api = time.time() - t0
    vm_id = vm["id"]
    vm_ip = vm["ip_address"]

    t_port22 = None
    t_ssh_ok = None
    first_attempt_time = None

    for attempt in range(120):
        now = time.time() - t0
        if t_port22 is None and check_port_22(vm_ip, timeout=0.1):
            t_port22 = now

        proc = subprocess.run(
            [
                "sshpass",
                "-p",
                VMPASS,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "ConnectTimeout=1",
                "-o",
                "LogLevel=ERROR",
                f"rajyavardhan@{vm_ip}",
                "cat /proc/uptime && systemd-analyze time 2>/dev/null || true",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            t_ssh_ok = time.time() - t0
            guest_diag = proc.stdout.strip().replace("\n", " | ")
            break
        time.sleep(0.3)

    # Now inspect systemd-analyze blame / critical-chain
    blame_proc = subprocess.run(
        [
            "sshpass",
            "-p",
            VMPASS,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=1",
            f"rajyavardhan@{vm_ip}",
            "systemd-analyze blame | head -n 3",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    blame = blame_proc.stdout.strip().replace("\n", " ; ")

    api("DELETE", f"/vms/{vm_id}")

    return {
        "run": run_idx,
        "vm_id": vm_id,
        "ip": vm_ip,
        "t_api": t_api,
        "t_port22": t_port22,
        "t_ssh_ok": t_ssh_ok,
        "guest_diag": guest_diag,
        "blame": blame,
    }


def main():
    print("Starting 5 consecutive node-a benchmark runs (10s gap)...")
    results = []
    for r in range(1, 6):
        res = run_single(r)
        results.append(res)
        p22 = f"{res['t_port22']:.3f} s" if res["t_port22"] else "N/A"
        ssh = f"{res['t_ssh_ok']:.3f} s" if res["t_ssh_ok"] else "N/A"
        print(
            f"Run {r}: {res['vm_id']} | API: {res['t_api']:.3f} s | Port 22: {p22} | SSH Ready: {ssh} | Guest: {res['guest_diag']} | Top blame: {res['blame']}"
        )
        if r < 5:
            print("  Waiting 10 seconds before next run...")
            time.sleep(10)


if __name__ == "__main__":
    main()
