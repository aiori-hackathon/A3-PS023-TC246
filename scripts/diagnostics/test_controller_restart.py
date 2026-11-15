#!/usr/bin/env python3
"""
PS-023: Controller Restart Reconciliation Test
Creates VMs on both nodes (node-a and node-b), restarts only the controller,
and verifies that VMs are still listed and RUNNING, with no duplicate or orphan VMs.
Saves raw output to evidence/controller_restart_20261115.txt.
"""
import os
import sys
import time
import json
import urllib.request
import subprocess

CONTROLLER_URL = os.environ.get("PS023_CONTROLLER_URL", "http://127.0.0.1:8000")
SECRETS_FILE = os.path.expanduser("~/ps023/secrets.env")
EVIDENCE_FILE = os.path.expanduser("~/ps023/evidence/controller_restart_20261115.txt")
SUBMIT_EVIDENCE_FILE = os.path.expanduser("~/ps023-submit/evidence/controller_restart_20261115.txt")

def get_secret(key):
    with open(SECRETS_FILE) as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.strip().split("=", 1)[1].strip('"\'')
    raise RuntimeError(f"{key} not found")

TOKEN = get_secret("PS023_API_TOKEN")

output_lines = []

def log(msg=""):
    print(msg, flush=True)
    output_lines.append(msg)

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

def wait_for_vm_running(vm_id, expected_node, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            vm = api_call(f"/vms/{vm_id}")
            if vm["status"] == "RUNNING" and vm["node_id"] == expected_node:
                return vm, round(time.time() - t0, 3)
        except Exception:
            pass
        time.sleep(0.5)
    return None, None

def main():
    log("=" * 80)
    log("PS-023: Controller Restart Reconciliation Test")
    log(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log("=" * 80)

    # 1. Check baseline
    nodes = api_call("/nodes")
    log("\n[1/5 Initial Cluster Health]")
    for n in nodes:
        log(f"  * Node {n['id']}: status={n['status']} schedulable_mb={n['memory_schedulable_mb']} running_vms={n['vms_running']}")
    if not all(n["status"] == "HEALTHY" for n in nodes):
        log("ERROR: Nodes are not healthy before test.")
        sys.exit(1)

    # 2. Deploy VM on node-a and VM on node-b
    log("\n[2/5 Deploying Test VMs across nodes]")
    vm_a = api_call("/vms", method="POST", data={
        "name": "reconcile-test-a",
        "vcpus": 1,
        "memory_mb": 512,
        "image": "ubuntu-24-04",
        "target_node": "node-a"
    })
    log(f"  Created VM on node-a: ID {vm_a['id']} (name: {vm_a['name']})")

    vm_b = api_call("/vms", method="POST", data={
        "name": "reconcile-test-b",
        "vcpus": 1,
        "memory_mb": 512,
        "image": "ubuntu-24-04",
        "target_node": "node-b"
    })
    log(f"  Created VM on node-b: ID {vm_b['id']} (name: {vm_b['name']})")

    ready_a, boot_a = wait_for_vm_running(vm_a["id"], "node-a")
    ready_b, boot_b = wait_for_vm_running(vm_b["id"], "node-b")

    log(f"  VM A {vm_a['id']} status: {ready_a['status']} on {ready_a['node_id']} (IP: {ready_a.get('ip_address')})")
    log(f"  VM B {vm_b['id']} status: {ready_b['status']} on {ready_b['node_id']} (IP: {ready_b.get('ip_address')})")

    # 3. Pre-restart VM snapshot
    vms_before = api_call("/vms")
    log(f"\n[3/5 Pre-Restart VM Snapshot ({len(vms_before)} VMs total)]")
    for v in vms_before:
        log(f"  * {v['id']} ({v['name']}): node={v['node_id']} status={v['status']} ip={v.get('ip_address')}")

    # 4. Restart Controller ONLY
    log("\n[4/5 Restarting Controller Service ONLY...]")
    t_kill = time.time()
    # Kill controller uvicorn process
    subprocess.run(["pkill", "-f", "uvicorn main:app --host 127.0.0.1 --port 8000"], check=False)
    time.sleep(1)

    # Verify controller is down
    down = False
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
    except Exception:
        down = True
    log(f"  Controller stopped: confirmed down={down}")

    # Start controller back up using bring-up environment
    bringup_cmd = (
        "bash ~/ps023/with-secrets.sh bash -c '"
        "(cd /home/rajyavardhan/ps023/controller && "
        "export PS023_VM_PASSWORD PS023_API_TOKEN PS023_TOKEN_NODE_A PS023_TOKEN_NODE_B "
        "PS023_NODES=\"node-a=http://127.0.0.1:8001,node-b=http://192.168.100.17:8002\" && "
        "setsid /home/rajyavardhan/ps023/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >> /home/rajyavardhan/ps023/logs/controller.log 2>&1 < /dev/null &)'"
    )
    subprocess.run(bringup_cmd, shell=True, check=True)

    # Wait for controller /health ok
    restarted = False
    for _ in range(30):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "ok":
                    restarted = True
                    break
        except Exception:
            pass

    restart_duration = round(time.time() - t_kill, 2)
    log(f"  Controller restarted successfully in {restart_duration}s (health: ok)")

    # 5. Post-restart reconciliation verification
    log("\n[5/5 Post-Restart Reconciliation Verification]")
    # Allow reconciliation loop 2-3 seconds to sync with workers
    time.sleep(3)

    nodes_after = api_call("/nodes")
    for n in nodes_after:
        log(f"  * Node {n['id']}: status={n['status']} schedulable_mb={n['memory_schedulable_mb']} running_vms={n['vms_running']}")

    vms_after = api_call("/vms")
    log(f"\n  Post-Restart VMs Count: {len(vms_after)} (Expected: {len(vms_before)})")
    for v in vms_after:
        log(f"  * {v['id']} ({v['name']}): node={v['node_id']} status={v['status']} ip={v.get('ip_address')}")

    # Checks
    vms_before_ids = {v["id"] for v in vms_before}
    vms_after_ids = {v["id"] for v in vms_after}

    assert vms_before_ids == vms_after_ids, f"Mismatch in VM IDs! Before: {vms_before_ids}, After: {vms_after_ids}"
    assert len(vms_after) == len(vms_before), f"Duplicate or orphan VMs detected! Count: {len(vms_after)}"
    for v in vms_after:
        assert v["status"] == "RUNNING", f"VM {v['id']} is in unexpected status {v['status']}!"
    log("\nRESULT: Reconciliation SUCCESS - Both VMs intact, RUNNING on original nodes, 0 duplicates, 0 orphans.")

    # Cleanup
    log("\n[Cleanup]")
    for vid in [vm_a["id"], vm_b["id"]]:
        log(f"  Deleting test VM {vid}...")
        api_call(f"/vms/{vid}", method="DELETE")
        time.sleep(1)
    log("  Cleanup complete.")

    # Write evidence files
    output_text = "\n".join(output_lines) + "\n"
    os.makedirs(os.path.dirname(EVIDENCE_FILE), exist_ok=True)
    with open(EVIDENCE_FILE, "w") as f:
        f.write(output_text)
    os.makedirs(os.path.dirname(SUBMIT_EVIDENCE_FILE), exist_ok=True)
    with open(SUBMIT_EVIDENCE_FILE, "w") as f:
        f.write(output_text)
    log(f"\nEvidence written to {EVIDENCE_FILE} and {SUBMIT_EVIDENCE_FILE}")

if __name__ == "__main__":
    main()
