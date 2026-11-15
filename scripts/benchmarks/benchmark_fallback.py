#!/usr/bin/env python3
import json
import os
import statistics
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


def run_benchmark(target_node, transport_label, runs=5):
    results_running = []
    results_ssh = []
    rows = []

    print(
        f"=== Fallback Benchmark: Pinned to {target_node} ({runs} Runs, transport: {transport_label}) ==="
    )
    print(
        "-------------------------------------------------------------------------------------------------"
    )
    print(
        "Run | VM ID       | Node   | IP             | Status RUNNING | SSH Ready (Full Boot) | Transport"
    )
    print(
        "----+-------------+--------+----------------+----------------+-----------------------+------------"
    )

    for i in range(1, runs + 1):
        t0 = time.time()
        vm = api(
            "POST",
            "/vms",
            {
                "name": f"fallback-bench-{target_node}-{i}",
                "vcpus": 1,
                "memory_mb": 512,
                "disk_gb": 4,
                "target_node": target_node,
            },
        )
        t_running = time.time() - t0
        vm_id = vm.get("id")
        vm_ip = vm.get("ip_address")
        node_id = vm.get("node_id")

        t_ssh_dur = None
        for attempt in range(60):
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
                    "true",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if proc.returncode == 0:
                t_ssh_dur = time.time() - t0
                break
            time.sleep(0.3)

        api("DELETE", f"/vms/{vm_id}")

        results_running.append(t_running)
        if t_ssh_dur is not None:
            results_ssh.append(t_ssh_dur)
            ssh_str = f"{t_ssh_dur:.3f} s"
        else:
            ssh_str = "TIMEOUT"

        row = f" {i:2d} | {vm_id:11s} | {node_id:6s} | {vm_ip:14s} | {t_running:.3f} s        | {ssh_str:21s} | {transport_label}"
        print(row)
        rows.append(row)

    print(
        "-------------------------------------------------------------------------------------------------"
    )
    summary_lines = [
        f"Metric 1: Controller API Create -> Status RUNNING ({target_node}, {runs} runs)",
        f"  Min    : {min(results_running):.3f} s",
        f"  Median : {statistics.median(results_running):.3f} s",
        f"  Max    : {max(results_running):.3f} s",
        "",
        f"Metric 2: Real Full Guest Boot (Create -> SSH Ready, {target_node}, {runs} runs)",
        f"  Min    : {min(results_ssh):.3f} s" if results_ssh else "  Min    : N/A",
        (
            f"  Median : {statistics.median(results_ssh):.3f} s"
            if results_ssh
            else "  Median : N/A"
        ),
        f"  Max    : {max(results_ssh):.3f} s" if results_ssh else "  Max    : N/A",
    ]
    for sl in summary_lines:
        print(sl)
    print(
        "=================================================================================================\n"
    )

    return rows, summary_lines


def main():
    header = """======================================================================
 Cloud Hypervisor Fallback Environment Benchmark
 Date: 2026-11-14
 Transport: Local Bridge / Nested Tap
 Host: AMD Ryzen 7 7445HS w/ Radeon 740M Graphics (12 vCPUs)
 Node A: Local Host (Fedora Linux, KVM direct)
 Node B: Local Nested VM (192.168.100.17, nested KVM, 4 vCPUs, 4GB RAM)
======================================================================
"""
    print(header)

    rows_a, sum_a = run_benchmark("node-a", "local-bridge", 5)
    rows_b, sum_b = run_benchmark("node-b", "nested-bridge", 5)

    full_output = (
        header
        + "\n"
        + "=== Fallback Benchmark: Pinned to node-a (5 Runs, transport: local-bridge) ===\n"
        + "-------------------------------------------------------------------------------------------------\n"
        + "Run | VM ID       | Node   | IP             | Status RUNNING | SSH Ready (Full Boot) | Transport\n"
        + "----+-------------+--------+----------------+----------------+-----------------------+------------\n"
        + "\n".join(rows_a)
        + "\n"
        + "-------------------------------------------------------------------------------------------------\n"
        + "\n".join(sum_a)
        + "\n=================================================================================================\n\n"
        + "=== Fallback Benchmark: Pinned to node-b (5 Runs, transport: nested-bridge) ===\n"
        + "-------------------------------------------------------------------------------------------------\n"
        + "Run | VM ID       | Node   | IP             | Status RUNNING | SSH Ready (Full Boot) | Transport\n"
        + "----+-------------+--------+----------------+----------------+-----------------------+------------\n"
        + "\n".join(rows_b)
        + "\n"
        + "-------------------------------------------------------------------------------------------------\n"
        + "\n".join(sum_b)
        + "\n=================================================================================================\n"
    )

    out_paths = [
        "/home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt",
        "/home/rajyavardhan/ps023-submit/evidence/boot_test_fallback_20261114.txt",
    ]
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(full_output)
    print(f"Benchmark results written to {out_paths}")


if __name__ == "__main__":
    main()
