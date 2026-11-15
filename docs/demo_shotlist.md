# PS-023: Demonstration Video Shotlist & Production Runbook
**Target Duration**: 5:00 to 7:00 minutes  
**Target Environment**: Primary Local Fallback Mode (Direct KVM Host Node A + Nested KVM Node B)  
**Resolution / Display**: 1920x1080 (1080p), Split Screen (Left: Browser Dashboard at `http://127.0.0.1:8000/dashboard/`; Right: Dual Terminal Panes)

---

## Scene 1: Platform Overview & Heterogeneous Architecture (0:00 – 0:50)

- **Visual Layout**: Fullscreen browser showing Dashboard **Overview** tab with real-time 3D topology and active node status.
- **Narrator Cue**:
  > "Welcome to PS-023. This is an enterprise-grade MicroVM orchestration platform powered by Cloud Hypervisor and Linux cgroups v2. We are demonstrating our primary local fallback deployment: Node A running direct KVM virtualization on the host, and Node B running inside an isolated nested KVM environment with its own dedicated subnet routing."
- **Actions**:
  1. Click **Nodes** tab: point out `node-a` (12 vCPUs, 15GB RAM) and `node-b` (4 vCPUs, 4GB RAM).
  2. Point out active cgroups v2 isolation indicators and live resource telemetry.
- **Verification**: Both nodes show `HEALTHY`, 0 active VMs.

---

## Scene 2: Pluggable Policy Scheduling & Placement Preview (0:50 – 1:45)

- **Visual Layout**: Left: Dashboard **Decisions** tab; Right: Terminal 1.
- **Narrator Cue**:
  > "Our scheduler features pluggable heuristic policies: `memory_aware`, `best_fit`, and `first_fit`. Before deploying, operators can preview placement decisions."
- **Terminal Command**:
  ```bash
  bash ~/ps023/with-secrets.sh bash -c '
  curl -s -H "Authorization: Bearer $PS023_API_TOKEN" \
    "http://127.0.0.1:8000/scheduler/preview?policy=best_fit&memory_mb=512" | jq .
  '
  ```
- **Key Display Elements**:
  - Show recommended node (`node-a` or `node-b` based on density fit).
  - Show policy comparison block comparing all 3 policies simultaneously.
- **Refusal Edge Case**:
  ```bash
  # Request 4096MB when no single node has 4GB free
  bash ~/ps023/with-secrets.sh bash -c '
  curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" \
    -d "{\"name\":\"oversized-test\",\"vcpus\":2,\"memory_mb\":4096,\"image\":\"ubuntu-24-04\"}" \
    http://127.0.0.1:8000/vms | jq .
  '
  ```
  - Highlight structured HTTP 409 refusal with candidate breakdown (`node-a: skipped: not enough memory`, `node-b: skipped: not enough memory`).

---

## Scene 3: MicroVM Launch & Stop Escalation Lifecycle (1:45 – 2:50)

- **Visual Layout**: Split screen (Browser **VMs** tab on left, Terminal on right).
- **Narrator Cue**:
  > "Deploying lightweight Cloud Hypervisor guests takes under a second at the API layer, with sub-350ms kernel initialization."
- **Terminal Commands**:
  ```bash
  # 1. Create VM on Node A
  bash ~/ps023/with-secrets.sh bash -c '
  curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" \
    -d "{\"name\":\"demo-guest-a\",\"vcpus\":1,\"memory_mb\":512,\"target_node\":\"node-a\"}" \
    http://127.0.0.1:8000/vms | jq "{id, name, node_id, status, ip_address, cgroups}"
  '
  ```
- **Actions in UI**:
  - VM card appears immediately with assigned IP `192.168.100.10`.
  - Demonstrate Stop Escalation:
    ```bash
    bash ~/ps023/with-secrets.sh bash -c '
    curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/vms/<VM_ID>/stop
    '
    ```
  - Explain the 30-second ACPI power button graceful period escalating to clean VMM shutdown without orphan processes.
  - Restart VM:
    ```bash
    bash ~/ps023/with-secrets.sh bash -c '
    curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/vms/<VM_ID>/start
    '
    ```
  - Status transitions back to `RUNNING`.

---

## Scene 4: In-Browser WebSocket Terminal Access (2:50 – 3:45)

- **Visual Layout**: Fullscreen browser on Dashboard **Terminals** tab.
- **Narrator Cue**:
  > "For secure multi-tenant management, PS-023 provides direct interactive WebSocket terminal sessions without exposing SSH ports or private keys to the open web."
- **Actions**:
  1. Click **Terminal** tab on `demo-guest-a`.
  2. In the integrated xterm.js prompt, execute:
     ```bash
     uname -a
     cat /proc/cpuinfo | grep 'model name' | head -n 1
     ip addr show eth0
     ```
  3. Show real-time streaming output directly inside the browser.

---

## Scene 5: High Availability Failover & Fencing (3:45 – 5:15) — *HIGHLIGHT*

- **Visual Layout**: Left: Dashboard **Failover / Events** tab; Right: Dual Terminal (Top: Host controller monitor; Bottom: Node B chaos terminal).
- **Narrator Cue**:
  > "Now for our centerpiece: zero-touch autonomous failover. We deploy an HA-protected MicroVM on Node B, simulate a sudden hard node failure, and observe sub-second cold evacuation."
- **Step 1: Deploy HA VM on Node B**:
  ```bash
  bash ~/ps023/with-secrets.sh bash -c '
  curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" \
    -d "{\"name\":\"ha-production-vm\",\"vcpus\":1,\"memory_mb\":512,\"target_node\":\"node-b\",\"ha\":true}" \
    http://127.0.0.1:8000/vms | jq "{id, name, node_id, status, ip_address, ha}"
  '
  ```
  - Point out assigned IP `10.77.0.10` on Node B.
- **Step 2: Inject Hard Worker Failure on Node B**:
  ```bash
  bash ~/ps023/with-secrets.sh bash -c '
  export NODE_B_SSH_HOST=192.168.100.17 NODE_B_SSH_USER=rajyavardhan NODE_B_SSH_PASS="$PS023_VM_PASSWORD"
  ./scripts/chaos_kill_node_b.sh worker
  '
  ```
- **Timeline on Screen**:
  - **T+0.0s**: Worker B stops responding.
  - **T+14.5s**: Controller misses 3 heartbeats; `node-b` transitions to `UNHEALTHY` (red indicator on dashboard).
  - **T+15.0s**: Evacuation reconciler triggers: `ha-production-vm` dynamically boots on surviving `node-a` in **0.51 seconds**!
  - Point out IP transitions to `192.168.100.10`; VM status returns to `RUNNING`.
- **Step 3: Recover Node B & Verify Split-Brain Fencing**:
  ```bash
  bash ~/ps023/with-secrets.sh bash -c '
  export NODE_B_SSH_HOST=192.168.100.17 NODE_B_SSH_USER=rajyavardhan NODE_B_SSH_PASS="$PS023_VM_PASSWORD"
  ./scripts/chaos_restore_node_b.sh worker
  '
  ```
  - Show Node B returning to `HEALTHY`.
  - Highlight that stale Cloud Hypervisor instances on Node B are killed by the controller's fencing pass within seconds, preventing split-brain data corruption.

---

## Scene 6: Controller Self-Healing & Zero-Orphan Reconciliation (5:15 – 6:15)

- **Visual Layout**: Split screen (Left: Dashboard; Right: Terminal).
- **Narrator Cue**:
  > "What happens if the central orchestrator itself crashes? In PS-023, the control plane is strictly decoupled from running hypervisors."
- **Terminal Command**:
  ```bash
  # Kill controller process
  pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8000'
  # Restart controller
  bash ~/ps023/with-secrets.sh bash -c '
  (cd /home/rajyavardhan/ps023/controller && setsid /home/rajyavardhan/ps023/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >> /home/rajyavardhan/ps023/logs/controller.log 2>&1 < /dev/null &)
  '
  ```
- **Show Result**:
  - Controller recovers in **2.06 seconds**.
  - Query `/vms`: existing guests on both Node A and Node B remain `RUNNING` with zero dropped VMs, zero duplicates, and zero orphan processes.

---

## Scene 7: Wrap-Up & Engineering Transparency (6:15 – 6:45)

- **Visual Layout**: Fullscreen presentation slide showing the **Limitations & Verification Index**.
- **Narrator Cue**:
  > "In summary: PS-023 demonstrates sub-second cold failover, multi-policy scheduling, and strict cgroups v2 resource guarantees. Every metric shown today is backed by automated repeat benchmark logs in our evidence repository. Thank you."
- **Final Visual**: Project GitHub repository and command output terminal showing green test suite.
