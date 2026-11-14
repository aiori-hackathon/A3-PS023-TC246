#!/usr/bin/env python3
"""
PS-023: Azure Chaos Repeats Benchmark Runner
Executes 3 runs of mode 'worker' and 3 runs of mode 'worker-preserve-vms' on Azure Node B.
Saves all raw outputs and structured telemetry to evidence/chaos_azure_repeats_20261114.txt.
"""
import os
import sys
import time
import json
import urllib.request
import subprocess

CONTROLLER_URL = os.environ.get("PS023_CONTROLLER_URL", "http://127.0.0.1:8000")
AZURE_IP = os.environ.get("NODE_B_PUBLIC_IP", "104.211.95.184")
SSH_KEY = os.environ.get("NODE_B_SSH_KEY", os.path.expanduser("~/.ssh/id_rsa"))
SECRETS_FILE = os.path.expanduser("~/ps023/secrets.env")
EVIDENCE_FILE = os.path.expanduser("~/ps023/evidence/chaos_azure_repeats_20261114.txt")

def get_token():
    with open(SECRETS_FILE) as f:
        for line in f:
            if line.startswith("PS023_API_TOKEN="):
                return line.strip().split("=", 1)[1].strip('"\'')
    raise RuntimeError("PS023_API_TOKEN not found in secrets.env")

TOKEN = get_token()

def api_call(path, method="GET", data=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{CONTROLLER_URL}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
        if content:
            return json.loads(content)
        return None

def wait_for_node(node_id, target_status, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        nodes = api_call("/nodes")
        for n in nodes:
            if n["id"] == node_id and n["status"] == target_status:
                return True
        time.sleep(1)
    return False

def wait_for_vm_running(vm_id, node_id, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        vms = api_call("/vms")
        for v in vms:
            if v["id"] == vm_id and v["status"] == "RUNNING" and v["node_id"] == node_id:
                return v
        time.sleep(1)
    return None

def wait_for_vms_empty(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        vms = api_call("/vms")
        if len(vms) == 0:
            return True
        time.sleep(1)
    return False

def main():
    runs = [
        ("worker", 1),
        ("worker", 2),
        ("worker", 3),
        ("worker-preserve-vms", 1),
        ("worker-preserve-vms", 2),
        ("worker-preserve-vms", 3)
    ]

    out_lines = []
    def log(msg=""):
        print(msg)
        out_lines.append(msg)

    log("=" * 80)
    log("PS-023: Azure Chaos Repeats Benchmark (6 Runs: 3 worker + 3 worker-preserve-vms)")
    log(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log(f"Target Host: Azure Node B ({AZURE_IP}) via SSH tunnel / sshuttle")
    log("=" * 80)
    log()

    summary_records = []

    for idx, (mode, run_num) in enumerate(runs, 1):
        log("-" * 80)
        log(f"RUN {idx}/6: Mode '{mode}' (Repeat #{run_num})")
        log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        log("-" * 80)

        # 1. Baseline verification
        nodes = api_call("/nodes")
        for n in nodes:
            log(f"  * Node {n['id']}: status={n['status']} schedulable_mb={n['memory_schedulable_mb']}")
        if not all(n["status"] == "HEALTHY" for n in nodes):
            log("ERROR: Nodes not healthy before starting run. Aborting.")
            sys.exit(1)

        # 2. Deploy HA VM on node-b
        vm_name = f"ha-azure-{mode[:6]}-r{run_num}"
        log(f"\n[Deploying HA VM '{vm_name}' to node-b...]")
        vm_req = {
            "name": vm_name,
            "vcpus": 1,
            "memory_mb": 512,
            "image": "ubuntu-24-04",
            "target_node": "node-b",
            "ha": True
        }
        vm = api_call("/vms", method="POST", data=vm_req)
        vm_id = vm["id"]
        log(f"  Created VM ID: {vm_id} (node: {vm['node_id']}, IP: {vm.get('ip_address')})")

        # Confirm RUNNING on node-b
        ready_vm = wait_for_vm_running(vm_id, "node-b", timeout=30)
        if not ready_vm:
            log("ERROR: VM failed to reach RUNNING state on node-b. Aborting.")
            sys.exit(1)
        log(f"  VM {vm_id} confirmed RUNNING on node-b (IP: {ready_vm.get('ip_address')})")

        # 3. Inject Failure
        log(f"\n[Executing chaos failure injection: {mode}...]")
        env = os.environ.copy()
        env["NODE_B_SSH_HOST"] = AZURE_IP
        env["NODE_B_SSH_KEY"] = SSH_KEY
        env["PS023_API_TOKEN"] = TOKEN
        env["PS023_CONTROLLER_URL"] = CONTROLLER_URL

        kill_res = subprocess.run(
            ["bash", os.path.expanduser("~/ps023/scripts/chaos_kill_node_b.sh"), mode],
            env=env,
            capture_output=True,
            text=True
        )
        log(kill_res.stdout)
        if kill_res.stderr:
            log("STDERR: " + kill_res.stderr)
        if kill_res.returncode != 0:
            log(f"ERROR: chaos_kill_node_b.sh failed with return code {kill_res.returncode}")
            sys.exit(1)

        # 4. Restore Node B & Verify Fencing
        log("\n[Restoring Node B & Verifying Fencing...]")
        restore_res = subprocess.run(
            ["bash", os.path.expanduser("~/ps023/scripts/chaos_restore_node_b.sh"), "worker"],
            env=env,
            capture_output=True,
            text=True
        )
        log(restore_res.stdout)
        if restore_res.stderr:
            log("STDERR: " + restore_res.stderr)
        if restore_res.returncode != 0:
            log(f"ERROR: chaos_restore_node_b.sh failed with return code {restore_res.returncode}")
            sys.exit(1)

        # 5. Extract metrics from VM detail
        evac_vm = None
        for v in api_call("/vms"):
            if v["id"] == vm_id:
                evac_vm = v
                break
        
        recovery_time = evac_vm.get("recovery_time_s") if evac_vm else None
        log(f"\nRun {idx} ({mode} #{run_num}) Summary:")
        log(f"  Evacuated VM {vm_id} status on node-a: {evac_vm.get('status') if evac_vm else 'MISSING'}")
        log(f"  Reported cold evacuation time: {recovery_time}s")

        # Parse detection delay from stdout
        detect_delay = None
        for l in kill_res.stdout.splitlines():
            if "detection delay:" in l:
                try:
                    detect_delay = float(l.split("detection delay:")[1].split("s")[0].strip())
                except Exception:
                    pass
            if "Total recovery time:" in l:
                try:
                    total_recovery = float(l.split("Total recovery time:")[1].split("s")[0].strip())
                except Exception:
                    pass

        summary_records.append({
            "run": idx,
            "mode": mode,
            "repeat": run_num,
            "vm_id": vm_id,
            "detect_delay_s": detect_delay,
            "cold_evac_s": recovery_time,
            "total_recovery_s": total_recovery if 'total_recovery' in locals() else None,
            "status_node_a": evac_vm.get("status") if evac_vm else "UNKNOWN"
        })

        # 6. Clean up VM on node-a
        log(f"\n[Cleaning up evacuated VM {vm_id} on node-a...]")
        api_call(f"/vms/{vm_id}", method="DELETE")
        wait_for_vms_empty(timeout=20)
        log("  VM cleaned up. 0 VMs running.")

        # 10s gap between runs
        if idx < len(runs):
            log("Waiting 10s gap before next run...")
            time.sleep(10)
        log()

    # Final summary table
    log("=" * 80)
    log("AZURE CHAOS EXPERIMENT SUMMARY (6 RUNS)")
    log("=" * 80)
    log(f"{'Run':<4} | {'Mode':<20} | {'Detect (s)':<12} | {'Cold Evac (s)':<14} | {'Total Rec (s)':<14} | {'Outcome'}")
    log("-" * 80)
    for r in summary_records:
        det = f"{r['detect_delay_s']:.2f}" if r['detect_delay_s'] is not None else "n/a"
        eva = f"{r['cold_evac_s']:.2f}" if r['cold_evac_s'] is not None else "n/a"
        tot = f"{r['total_recovery_s']:.2f}" if r['total_recovery_s'] is not None else "n/a"
        log(f"{r['run']:<4} | {r['mode']:<20} | {det:<12} | {eva:<14} | {tot:<14} | {r['status_node_a']}")
    log("=" * 80)

    # Compute stats for worker and worker-preserve-vms
    worker_totals = [r["total_recovery_s"] for r in summary_records if r["mode"] == "worker" and r["total_recovery_s"] is not None]
    preserve_totals = [r["total_recovery_s"] for r in summary_records if r["mode"] == "worker-preserve-vms" and r["total_recovery_s"] is not None]

    if worker_totals:
        log(f"Mode 'worker' (3 runs) Total Recovery: Min={min(worker_totals):.2f}s, Median={sorted(worker_totals)[1]:.2f}s, Max={max(worker_totals):.2f}s")
    if preserve_totals:
        log(f"Mode 'worker-preserve-vms' (3 runs) Total Recovery: Min={min(preserve_totals):.2f}s, Median={sorted(preserve_totals)[1]:.2f}s, Max={max(preserve_totals):.2f}s")

    os.makedirs(os.path.dirname(EVIDENCE_FILE), exist_ok=True)
    with open(EVIDENCE_FILE, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    log(f"\nFull evidence log saved to: {EVIDENCE_FILE}")

if __name__ == "__main__":
    main()
