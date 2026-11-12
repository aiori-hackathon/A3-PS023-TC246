# PS-023 Production Demo Runbook & Evaluation Guide
**Project ID**: A3-PS023-TC246  
**System**: Intelligent Hypervisor Controller for Resource Management  
**Architecture**: Two-Node MicroVM Cluster (`node-a` Bare-metal Host + `node-b` Hypervisor Worker)  
**Status**: Production Ready & Demonstration Hardened (12 November 2026)

---

## 1. Safety Rules & Operational Standards

1. **Host-Key Verification for Infrastructure**:
   - Every SSH connection to fixed infrastructure nodes (Node B at `192.168.100.17` or Azure VM `104.211.95.184`) must enforce strict host-key verification:
     `-o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts`
   - Never disable host key verification or discard keys to `/dev/null` for infrastructure nodes.
2. **Dynamic Guest MicroVM Host Keys**:
   - MicroVMs generate fresh SSH host keys on direct kernel boot. To connect safely while preventing collision with reused slot IPs:
     `ssh-keygen -R "$VM_IP" 2>/dev/null; ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=~/.ssh/known_hosts ...`
3. **Exact VM ID Targeting**:
   - Every lifecycle operation (stop, start, delete) **must** reference the exact UUID returned by POST `/vms` (e.g. `VM_ID=$(echo "$RESP" | jq -r .id)`).
   - **Never** perform wildcard deletions, prefix matches, or delete from raw lists.
   - The pre-existing baseline VMs (`ps-023` and `ps-023-2`) on `node-a` must remain untouched.
4. **Resilient Node Filtering**:
   - Never access node arrays by numeric index (`nodes[0]`). Node order in JSON responses is non-deterministic.
   - Filter explicitly by identifier: `.[] | select(.id == "node-b")`.
5. **Cgroup Worker Mapping**:
   - The controller VM identifier (`id`, e.g. `vm-a1b2c3d4`) differs from the worker-local hypervisor identifier (`worker_vm_id`, e.g. `vm-e5f6g7h8`).
   - Always locate the cgroup using dynamic lookup: `find /sys/fs/cgroup -name "ps023-vmm-${WORKER_VM_ID}"`.
6. **No Speculative Claims**:
   - Cloud Hypervisor microVMs run direct-kernel boot without shared SAN/Ceph storage; true live memory migration is out-of-scope for microVMs. The system instead implements deterministic cold HA failover with stale ghost fencing.
   - WireGuard is blocked by UDP-filtering networks (e.g. hostel Wi-Fi); use the deterministic Local Fallback or SSH Tunnel mode.

---

## 2. Cluster Deployment Modes

### Mode 1: Local Nested-VM Fallback (Primary / Recommended for Demo)
100% offline, fully deterministic, zero external cloud dependencies:
```bash
# Bring up cluster (starts br-ps023, boots local nested node-b, worker A, controller):
bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
```
*Expected cluster state*:
- `node-a`: `http://127.0.0.1:8001` (HEALTHY, ~5000MB schedulable)
- `node-b`: `http://192.168.100.17:8002` (HEALTHY, ~2500MB schedulable)
- Controller: `http://127.0.0.1:8000` (HEALTHY)

### Mode 2: Azure Hybrid Cloud (Dev-Tunnel Mode)
When Azure VM `ps023-node-b` is powered on and accessible:
```bash
# 1. Start Azure VM (if deallocated):
az vm start -g rg-ps023 -n ps023-node-b

# 2. Start persistent SSH tunnel service and subnet proxy:
systemctl --user start ps023-ssh-tunnel
~/ps023/.venv/bin/sshuttle -r ubuntu@104.211.95.184 192.168.200.0/24 --daemon --pidfile=/tmp/sshuttle.pid

# 3. Bring up cluster in SSH tunnel mode:
TUNNEL_MODE=ssh bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
```

---

## 3. Environment Preparation

Open a terminal and load credentials safely without printing secrets:

```bash
export PS023_API_TOKEN=$(grep -E '^PS023_API_TOKEN=' ~/ps023/secrets.env | cut -d= -f2- | tr -d '"'"')
export PS023_VM_PASSWORD=$(grep -E '^PS023_VM_PASSWORD=' ~/ps023/secrets.env | cut -d= -f2- | tr -d '"'"')
AUTH="Authorization: Bearer $PS023_API_TOKEN"
BASE="http://127.0.0.1:8000"
```

---

## 4. Live Evaluation Sequence

### Step 1: Health, Security & Node Discovery (1 min)

#### 1.1 Authentication Enforcement
Verify that unauthenticated access is rejected with `HTTP 401`:
```bash
curl -s -o /dev/null -w "Unauthenticated access: HTTP %{http_code} (Expected 401)\n" $BASE/nodes
```

#### 1.2 Cluster Discovery & Cgroups Verification
Query all nodes and verify both report `HEALTHY` with active cgroups:
```bash
curl -s -H "$AUTH" $BASE/nodes | jq -r '.[] | "Node: \(.id) | Status: \(.status) | Schedulable RAM: \(.memory_schedulable_mb)MB | Cgroups: \(.cgroups_enabled)"'
```
*Expected Output*: Both `node-a` and `node-b` display `Status: HEALTHY` and `Cgroups: true`.

---

### Step 2: Schedulable Memory Invariant & Rejection (2 min)

#### 2.1 Schema Validation (Exceeds Max Supported VM Size)
Request 99999 MB to trigger Pydantic schema validation:
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST $BASE/vms \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name": "vm-too-big", "vcpus": 1, "memory_mb": 99999, "disk_gb": 4}'
```
*Expected*: `HTTP Status: 422` (Unprocessable Entity, `le=8192` constraint).

#### 2.2 Schedulable Capacity Rejection
Request 8000 MB (exceeds individual node schedulable RAM) to trigger scheduler rejection:
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST $BASE/vms \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name": "vm-capacity-refusal", "vcpus": 1, "memory_mb": 8000, "disk_gb": 4}'
```
*Expected*: `HTTP Status: 409` with per-node candidate evaluation breakdown:
```json
{
  "detail": {
    "error": "placement_failed",
    "requested_mb": 8000,
    "decision": {
      "selected": null,
      "reason": "no candidate node had capacity or was eligible",
      "candidates": [
        {"node_id": "node-a", "verdict": "refused: insufficient memory (8000MB > schedulable)"},
        {"node_id": "node-b", "verdict": "refused: insufficient memory (8000MB > schedulable)"}
      ]
    }
  }
}
```

#### 2.3 Verify Decision Audit Trail
```bash
curl -s -H "$AUTH" "$BASE/decisions?limit=1" | jq .
```

---

### Step 3: Safe VM Lifecycle & Exact-ID Targeting (3 min)

#### 3.1 Provision Targeted VM on Node B
Provision a 512MB microVM pinned to `node-b`:
```bash
CREATE_RESP=$(curl -s -X POST $BASE/vms \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name": "demo-vm-01", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "target_node": "node-b"}')

echo "$CREATE_RESP" | jq .

VM_ID=$(echo "$CREATE_RESP" | jq -r .id)
WORKER_VM_ID=$(echo "$CREATE_RESP" | jq -r .worker_vm_id)
NODE_ID=$(echo "$CREATE_RESP" | jq -r .node_id)
echo "Created: Controller ID=$VM_ID | Worker VM ID=$WORKER_VM_ID | Node=$NODE_ID"
```
*Expected*: `HTTP 201`, `status: "RUNNING"`, `cgroups: true`.

#### 3.2 Guest Reachability
Wait 5 seconds for network initialization, then test ping and SSH uptime:
```bash
VM_IP=$(curl -s -H "$AUTH" "$BASE/vms/$VM_ID" | jq -r .ip_address)
echo "Pinging guest at $VM_IP..."
ping -c 2 -W 1 "$VM_IP"

echo "Executing SSH uptime on guest..."
ssh-keygen -R "$VM_IP" 2>/dev/null
sshpass -p "$PS023_VM_PASSWORD" ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=~/.ssh/known_hosts -o ConnectTimeout=5 "rajyavardhan@$VM_IP" "uptime"
```
*Expected*: 0% packet loss, SSH returns valid guest uptime.

---

### Step 4: Cgroups v2 Resource Enforcement Verification (2 min)

Inspect kernel cgroups on Node B corresponding to `$WORKER_VM_ID`:
```bash
sshpass -p "$PS023_VM_PASSWORD" ssh -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts \
  rajyavardhan@192.168.100.17 \
  "CG=\$(find /sys/fs/cgroup -name \"ps023-vmm-${WORKER_VM_ID}\" 2>/dev/null | head -1) && \
   echo \"Cgroup Directory: \$CG\" && \
   echo \"memory.max: \$(cat \$CG/memory.max)\" && \
   echo \"cpu.max: \$(cat \$CG/cpu.max)\" && \
   echo \"pids.max: \$(cat \$CG/pids.max)\" && \
   echo \"cgroup.procs: \$(cat \$CG/cgroup.procs)\""
```
*Expected Verified Limits*:
- `memory.max`: `671088640` (640MB = 512MB RAM + 128MB hypervisor overhead)
- `cpu.max`: `125000 100000` (1 vCPU × 1.25 burst quota)
- `pids.max`: `256`
- `cgroup.procs`: Active Cloud Hypervisor VMM process PID

---

### Step 5: Worker Restart Survival on Node B (2 min)

Demonstrate that worker service restarts do NOT kill running guest VMs (`KillMode=process` and `DelegateSubgroup=service`):

```bash
# 1. Restart worker unit on Node B:
sshpass -p "$PS023_VM_PASSWORD" ssh -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts \
  rajyavardhan@192.168.100.17 "sudo systemctl restart ps023-worker"

# 2. Verify VMM process is still alive:
sshpass -p "$PS023_VM_PASSWORD" ssh -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts \
  rajyavardhan@192.168.100.17 "ps aux | grep -E '[c]loud-hypervisor.*${WORKER_VM_ID}'"

# 3. Verify guest still answers SSH:
sshpass -p "$PS023_VM_PASSWORD" ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=~/.ssh/known_hosts \
  "rajyavardhan@$VM_IP" "uptime"

# 4. Verify controller reports VM status as RUNNING:
curl -s -H "$AUTH" "$BASE/vms/$VM_ID" | jq '{id, status, cgroups}'
```
*Expected*: The guest continues running uninterrupted and answers SSH throughout the worker restart.

---

### Step 6: Graceful Teardown by Exact ID (1 min)

#### 6.1 Stop the Target VM
```bash
curl -s -X POST -H "$AUTH" "$BASE/vms/$VM_ID/stop" | jq '{id, status}'
```
*Expected*: `status: "STOPPED"`, `cgroups: false`.

#### 6.2 Delete the Target VM
```bash
DEL_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH" "$BASE/vms/$VM_ID")
echo "Delete VM response: HTTP $DEL_CODE (Expected 204)"
```

#### 6.3 Verify Cleanup
```bash
curl -s -H "$AUTH" "$BASE/vms" | jq .
```
*Expected*: Returns empty list `[]`. Baseline VMs remain untouched.

---

### Step 7: Automated Test Suite (1 min)

Execute the full test suite covering API endpoints, database security, scheduler invariants, cgroups v2, and VMM cleanup:

```bash
cd ~/ps023
.venv/bin/pytest tests/ controller/ worker/
```
*Expected Output*:
```text
================== 162 passed, 2 skipped, 1 warning in ~13s ==================
```

---

## 5. Safe Cluster Shutdown

To stop all cluster background processes safely without affecting unrelated systems:

```bash
# 1. Stop Controller and Worker A by exact host:port binding:
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8000' 2>/dev/null || true
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8001' 2>/dev/null || true

# 2. Stop local nested Node B VMM (targeting exact socket path):
OUTER_PID=$(pgrep -f "api-socket path=$HOME/ps023/outer/outer.sock" 2>/dev/null || true)
if [ -n "$OUTER_PID" ]; then
  kill "$OUTER_PID" 2>/dev/null || true
fi

# 3. If Azure Hybrid mode was used, stop tunnels and deallocate VM:
systemctl --user stop ps023-ssh-tunnel 2>/dev/null || true
pkill -f 'sshuttle' 2>/dev/null || true
az vm deallocate -g rg-ps023 -n ps023-node-b 2>/dev/null || true
```
