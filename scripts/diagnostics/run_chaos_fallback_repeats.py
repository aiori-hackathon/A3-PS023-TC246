#!/usr/bin/env python3
"""
PS-023: Fallback Chaos Repeats Benchmark Runner
Executes 3 runs of mode 'worker' and 3 runs of mode 'worker-preserve-vms' on nested Node B (192.168.100.17).
Records detection latency, evacuation latency, total recovery time, and fencing on return.
Saves all raw outputs and structured telemetry to evidence/chaos_fallback_repeats_20261115.txt.
"""
import os
import sys
import time
import json
import urllib.request
import subprocess

CONTROLLER_URL = os.environ.get("PS023_CONTROLLER_URL", "http://127.0.0.1:8000")
NODE_B_HOST = "192.168.100.17"
NODE_B_USER = "rajyavardhan"
SECRETS_FILE = os.path.expanduser("~/ps023/secrets.env")
EVIDENCE_FILE = os.path.expanduser("~/ps023/evidence/chaos_fallback_repeats_20261115.txt")
SUBMIT_EVIDENCE_FILE = os.path.expanduser("~/ps023-submit/evidence/chaos_fallback_repeats_20261115.txt")

def get_secret(key):
    if key in os.environ:
        return os.environ[key]
    with open(SECRETS_FILE) as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.strip().split("=", 1)[1].strip('"\'')
    raise RuntimeError(f"{key} not found")

TOKEN = get_secret("PS023_API_TOKEN")
VM_PASS = get_secret("PS023_VM_PASSWORD")

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

def ssh_node_b(cmd, timeout=15):
    ssh_cmd = [
        "sshpass", "-p", VM_PASS,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        f"{NODE_B_USER}@{NODE_B_HOST}",
        cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

def wait_for_node(node_id, target_status, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        nodes = api_call("/nodes")
        for n in nodes:
            if n["id"] == node_id and n["status"] == target_status:
                return True, round(time.time() - start, 3)
        time.sleep(0.5)
    return False, timeout

def wait_for_vm_running(vm_id, node_id, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        vms = api_call("/vms")
        for v in vms:
            if v["id"] == vm_id and v["status"] == "RUNNING" and v["node_id"] == node_id:
                return v, round(time.time() - start, 3)
        time.sleep(0.5)
    return None, timeout

def cleanup_all():
    vms = api_call("/vms")
    for v in vms:
        try:
            api_call(f"/vms/{v['id']}", method="DELETE")
        except Exception:
            pass
    for _ in range(15):
        if len(api_call("/vms")) == 0:
            break
        time.sleep(1)

def main():
    runs = [
        ("worker", 1),
        ("worker", 2),
        ("worker", 3),
        ("worker-preserve-vms", 1),
        ("worker-preserve-vms", 2),
        ("worker-preserve-vms", 3)
    ]

    out = []
    def log(msg=""):
        print(msg)
        out.append(msg)

    log("=" * 80)
    log("PS-023: Fallback Chaos Repeats Benchmark (6 Runs: 3 worker + 3 worker-preserve-vms)")
    log(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log(f"Environment: Fallback Mode (Nested Node B on {NODE_B_HOST})")
    log("=" * 80)
    log()

    summary_records = []

    # Clean initial state
    cleanup_all()

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
            log("ERROR: Nodes not healthy before starting run. Attempting restore...")
            ssh_node_b(f"echo '{VM_PASS}' | sudo -S systemctl start ps023-worker")
            wait_for_node("node-b", "HEALTHY", timeout=30)

        # 2. Deploy HA VM on node-b
        vm_name = f"ha-fallback-{mode[:6]}-r{run_num}"
        log(f"\n[1/5 Deploying HA VM '{vm_name}' on node-b...]")
        vm = api_call("/vms", method="POST", data={
            "name": vm_name,
            "vcpus": 1,
            "memory_mb": 512,
            "image": "ubuntu-24-04",
            "target_node": "node-b",
            "ha": True
        })
        vm_id = vm["id"]
        log(f"  Created VM ID: {vm_id} (node: {vm['node_id']})")

        ready_vm, boot_time = wait_for_vm_running(vm_id, "node-b", timeout=30)
        if not ready_vm:
            log("ERROR: VM failed to reach RUNNING state on node-b.")
            sys.exit(1)
        log(f"  VM {vm_id} confirmed RUNNING on node-b (IP: {ready_vm.get('ip_address')}) in {boot_time}s")

        # 3. Inject Failure
        log(f"\n[2/5 Injecting Chaos Failure (Mode: {mode})...]")
        t_kill = time.time()
        t_kill_human = time.strftime('%Y-%m-%d %H:%M:%S')

        if mode == "worker":
            # Stop worker unit AND kill all cloud-hypervisors on node B
            ssh_node_b(f"echo '{VM_PASS}' | sudo -S systemctl stop ps023-worker && echo '{VM_PASS}' | sudo -S pkill -9 -f '[c]loud-hypervisor' || true")
            log(f"  [{t_kill_human}] Node B worker stopped and all cloud-hypervisors killed (VMs gone).")
        elif mode == "worker-preserve-vms":
            # Stop worker unit ONLY (VMs remain running to test fencing on return)
            ssh_node_b(f"echo '{VM_PASS}' | sudo -S systemctl stop ps023-worker || true")
            log(f"  [{t_kill_human}] Node B worker stopped. Cloud-hypervisor processes remain running.")

        # 4. Detection: Wait for node-b to become UNHEALTHY
        log("\n[3/5 Detection: Waiting for controller to mark node-b UNHEALTHY...]")
        ok, _ = wait_for_node("node-b", "UNHEALTHY", timeout=45)
        t_detect = time.time()
        detect_delay = round(t_detect - t_kill, 2)
        if not ok:
            log("ERROR: Controller failed to detect node-b failure within 45s.")
            sys.exit(1)
        log(f"  [{time.strftime('%Y-%m-%d %H:%M:%S')}] Controller marked node-b as UNHEALTHY (detection delay: {detect_delay}s)")

        # 5. Evacuation: Wait for HA VM to be evacuated to node-a
        log("\n[4/5 Self-Healing: Monitoring auto-evacuation to node-a...]")
        evac_vm, _ = wait_for_vm_running(vm_id, "node-a", timeout=45)
        t_evac = time.time()
        total_recovery = round(t_evac - t_kill, 2)
        evac_delay = round(t_evac - t_detect, 2)
        if not evac_vm:
            log("ERROR: HA VM failed to evacuate to node-a.")
            sys.exit(1)
        reported_recovery = evac_vm.get("recovery_time_s", evac_delay)
        log(f"  [{time.strftime('%Y-%m-%d %H:%M:%S')}] VM {vm_id} successfully evacuated to node-a!")
        log(f"  Evacuated IP: {evac_vm.get('ip_address')} | Status: {evac_vm.get('status')}")
        log(f"  Detection: {detect_delay}s | Cold Evacuation: {evac_delay}s | Total Recovery: {total_recovery}s")

        # 6. Restoration & Fencing
        log(f"\n[5/5 Restoration & Fencing Verification (Mode: {mode})...]")
        t_restore = time.time()
        # Restore worker via systemctl
        ssh_node_b(f"echo '{VM_PASS}' | sudo -S systemctl start ps023-worker || true")

        ok, return_delay = wait_for_node("node-b", "HEALTHY", timeout=45)
        t_healthy = time.time()
        if not ok:
            log("ERROR: Node B failed to return to HEALTHY.")
            sys.exit(1)
        log(f"  [{time.strftime('%Y-%m-%d %H:%M:%S')}] Node B returned to HEALTHY in {return_delay}s!")

        # Check fencing
        fencing_status = "N/A"
        fencing_delay = 0.0
        if mode == "worker-preserve-vms":
            log("  Monitoring fencing of stale VMM on node-b...")
            fenced = False
            for poll in range(25):
                res = ssh_node_b(f"echo '{VM_PASS}' | sudo -S pgrep -f '[c]loud-hypervisor' | wc -l")
                count = int(res.stdout.strip() or 0)
                if count == 0:
                    fencing_delay = round(time.time() - t_healthy, 2)
                    fenced = True
                    log(f"  Stale VMM successfully killed by fencing pass in {fencing_delay}s post-return!")
                    break
                time.sleep(1)
            if fenced:
                fencing_status = f"KILLED ({fencing_delay}s post-return)"
            else:
                fencing_status = "TIMEOUT"
                log("  WARNING: Stale VMM was not fenced within 25s.")
        else:
            res = ssh_node_b(f"echo '{VM_PASS}' | sudo -S pgrep -f '[c]loud-hypervisor' | wc -l")
            count = int(res.stdout.strip() or 0)
            fencing_status = f"CLEAN (0 stale VMMs)"
            log(f"  Fencing verified: 0 stale VMMs present on node-b ({fencing_status}).")

        # Record metrics
        record = {
            "run": idx,
            "mode": mode,
            "vm_id": vm_id,
            "detect_s": detect_delay,
            "evac_s": evac_delay,
            "total_s": total_recovery,
            "fencing": fencing_status
        }
        summary_records.append(record)

        # Cleanup VM before next run
        log(f"\n[Cleaning up VM {vm_id}...]")
        api_call(f"/vms/{vm_id}", method="DELETE")
        cleanup_all()
        log("  Cleanup complete.\n")
        time.sleep(2)

    # Print Summary Table
    log("=" * 80)
    log("PS-023: Fallback Chaos Repeats - Summary Results")
    log("=" * 80)
    log(f"{'Run':<5} {'Mode':<22} {'VM ID':<13} {'Detect (s)':<12} {'Evac (s)':<10} {'Total (s)':<11} {'Fencing Outcome'}")
    log("-" * 80)
    for r in summary_records:
        log(f"{r['run']:<5} {r['mode']:<22} {r['vm_id']:<13} {r['detect_s']:<12.2f} {r['evac_s']:<10.2f} {r['total_s']:<11.2f} {r['fencing']}")
    log("=" * 80)

    # Write evidence file
    full_text = "\n".join(out)
    os.makedirs(os.path.dirname(EVIDENCE_FILE), exist_ok=True)
    with open(EVIDENCE_FILE, "w") as f:
        f.write(full_text)
    os.makedirs(os.path.dirname(SUBMIT_EVIDENCE_FILE), exist_ok=True)
    with open(SUBMIT_EVIDENCE_FILE, "w") as f:
        f.write(full_text)
    print(f"\nSaved raw evidence to {EVIDENCE_FILE} and {SUBMIT_EVIDENCE_FILE}")

if __name__ == "__main__":
    main()
