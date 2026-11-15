#!/usr/bin/env python3
import os
import sys
import time
import json
import statistics
import subprocess
import urllib.request

def main():
    target_node = sys.argv[1] if len(sys.argv) > 1 else "node-b"
    runs_count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    token = os.environ.get("PS023_API_TOKEN", "")
    vmpass = os.environ.get("PS023_VM_PASSWORD", "")
    ctrl_url = os.environ.get("CONTROLLER_URL", "http://127.0.0.1:8000")
    
    def api(method, path, body=None):
        url = ctrl_url + path
        headers = {"Authorization": "Bearer " + token}
        data = json.dumps(body).encode() if body else None
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=40) as resp:
            content = resp.read().decode()
            return json.loads(content) if content else {}

    print(f"=== Real MicroVM Boot & SSH Latency Benchmark via Controller (Pinned to {target_node}, {runs_count} Runs) ===")
    print("-------------------------------------------------------------------------------------------------")
    print("Run | VM ID       | Node   | IP             | Status RUNNING | SSH Ready (Full Boot) | Transport")
    print("----+-------------+--------+----------------+----------------+-----------------------+------------")
    
    transport_label = "ssh-tunnel" if target_node == "node-b" else "local-bridge"
    runs_running = []
    runs_ssh = []

    for i in range(1, runs_count + 1):
        vm_name = f"bench-{target_node}-{i}"
        t0 = time.time()
        
        vm = api("POST", "/vms", {
            "name": vm_name,
            "vcpus": 1,
            "memory_mb": 512,
            "disk_gb": 4,
            "target_node": target_node
        })
        
        t_running = time.time() - t0
        vm_id = vm.get("id")
        vm_ip = vm.get("ip_address")
        node_id = vm.get("node_id")
        
        # Test SSH readiness
        t_ssh = None
        for attempt in range(60):
            p = subprocess.run([
                "sshpass", "-p", vmpass,
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=1",
                "-o", "LogLevel=ERROR",
                f"rajyavardhan@{vm_ip}", "true"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if p.returncode == 0:
                t_ssh = time.time() - t0
                break
            time.sleep(0.3)
            
        # Clean up VM
        api("DELETE", f"/vms/{vm_id}")
        
        runs_running.append(t_running)
        if t_ssh is not None:
            runs_ssh.append(t_ssh)
            ssh_str = f"{t_ssh:.3f} s"
        else:
            ssh_str = "TIMEOUT"
            
        print(f" {i:2d} | {vm_id:11s} | {node_id:6s} | {vm_ip:14s} | {t_running:.3f} s        | {ssh_str:21s} | {transport_label}")

    print("-------------------------------------------------------------------------------------------------")
    print(f"Metric 1: Controller API Create -> Status RUNNING ({runs_count} runs)")
    print(f"  Min    : {min(runs_running):.3f} s")
    print(f"  Median : {statistics.median(runs_running):.3f} s")
    print(f"  Max    : {max(runs_running):.3f} s")
    print()
    if runs_ssh:
        print(f"Metric 2: Real Full Guest Boot (Create -> SSH Ready, {runs_count} runs)")
        print(f"  Min    : {min(runs_ssh):.3f} s")
        print(f"  Median : {statistics.median(runs_ssh):.3f} s")
        print(f"  Max    : {max(runs_ssh):.3f} s")
    print("=================================================================================================")

if __name__ == "__main__":
    main()
