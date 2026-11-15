# PS-023: Live Demonstration Runbook & Script
**Duration**: ~10–12 minutes  
**Target Environments**: 
- **Local Fallback Mode (Primary Demo / Tested Live)**: Node A (Host Fedora Linux direct KVM) + Node B (Nested KVM VM on `192.168.100.17`). Azure VM `ps023-node-b` stays deallocated.
- **Azure Hybrid Mode (Recorded Reference Runs from 13–14 Nov 2026)**: Laptop (Node A) + Azure Standard_D2s_v4 (Node B on `10.100.0.2`). Transport modes evaluated: `ssh-tunnel` (recorded 13–14 Nov); `wireguard` verified on a dedicated mobile hotspot only (venue hostel Wi-Fi blocks UDP 51820).

---

## Pre-Flight Preparation (2 minutes before presentation)

1. **Verify Environment & Secrets**:
   ```bash
   # Ensure secrets exist and Azure VM remains deallocated (read-only check)
   az vm get-instance-view -g rg-ps023 -n ps023-node-b --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
   # Expected output: VM deallocated
   ```

2. **Bring Up the Fallback Cluster**:
   ```bash
   # Prime sudo and launch bring-up in local fallback mode
   bash ~/ps023/with-secrets.sh bash -c 'echo "$PS023_VM_PASSWORD" | sudo -S -v && bash ~/ps023/bring-up.sh'
   ```
   **Expected Output**:
   ```text
   === 1. host network
   bridge and 8 TAP devices ready
   === 2. node-b setup
   node-b
   === 3. node-b inner network and worker
   worker B ok
   === 4. route to the inner network
   10.77.0.0/24 via 192.168.100.17 dev br-ps023
   === 5. worker A and controller on the host
   worker A ok
   controller ok
   === 6. cluster state
   nodes: node-a=HEALTHY(...) node-b=HEALTHY(...)
   host VMMs: 1 (1 expected: node-b)
   READY.
   ```

3. **Open Dashboard** [Verified by user on 2026-11-15]:
   - Open browser at `http://127.0.0.1:8000/dashboard/`.
   - Enter `PS023_API_TOKEN` (never paste or speak on screen).
   - Point out: Real-time 3D cluster topology, active nodes, hardware resource meters.

---

## Act 1: Architecture & Resilient Dashboard (2 minutes) [Partial: 7 of 8 views verified by user on 2026-11-15]

**Talking Points**:
- PS-023 orchestrates Cloud Hypervisor MicroVMs across heterogeneous compute nodes using direct KVM virtualization.
- Controller communicates with Worker daemons via authenticated REST APIs with strict timeouts and heartbeat leases.
- Tour the Dashboard tabs:
  - **Overview** [Verified by user on 2026-11-15]: Real-time cluster status, active VM counter, schedulable RAM.
  - **Nodes** [Verified by user on 2026-11-15]: Live node cards: `node-a` (12 vCPUs / 16GB), `node-b` (local nested node B = 4 vCPU / 4 GB; Azure node B = 2 vCPU / 8 GiB), memory headroom, cgroups v2 status.
  - **VMs** [Verified by user on 2026-11-15]: Deployed guests, IP assignments, direct console actions.
  - **Decisions** [Verified by user on 2026-11-15]: Real-time structured placement reasoning log.
  - **Events** [Verified by user on 2026-11-15]: Real-time cluster event stream and audit log.
  - **Images** [Verified by user on 2026-11-15]: OS catalog featuring Ubuntu 24.04 LTS, Debian 12, Alpine 3.20, and CirrOS with checksums (Debian/Alpine/CirrOS catalog entries marked "not boot-tested").
  - **Terminal** [Verified by user on 2026-11-15]: In-browser WebSocket terminal into running MicroVMs without exposing guest SSH publicly.
  - **Failover** [NOT VERIFIED]: Dedicated cluster high-availability monitor.

---

## Act 2: Pluggable Scheduling & Placement Preview (2 minutes) [VERIFIED: evidence in controller API responses]

Demonstrate the three placement algorithms (`memory_aware`, `best_fit`, `first_fit`) and live preview.

1. **Query Placement Preview API**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   curl -s -H "Authorization: Bearer $PS023_API_TOKEN" "http://127.0.0.1:8000/scheduler/preview?policy=best_fit&memory_mb=512" | python3 -m json.tool
   '
   ```
   **Expected Output**:
   - `policy`: `best_fit`
   - `recommended_node`: `node-b` (Reason: `smallest sufficient memory` — packs 512MB onto 2.5GB node rather than consuming 8GB node).
   - `policy_choices`:
     - `memory_aware` -> `node-a` (`highest available memory`)
     - `first_fit` -> `node-a` (`first fit with sufficient memory`)
     - `best_fit` -> `node-b` (`smallest sufficient memory`)

---

## Act 3: MicroVM Boot & SSH Latency Benchmark (2 minutes) [VERIFIED: real benchmark evidence]

Demonstrate sub-second microVM creation and real Linux guest boot speed.

1. **Show Benchmarked Latency Ranges**:
   - **Node A (Direct Host KVM)**:
     - API Create -> Status `RUNNING`: **0.772 s – 0.997 s** (Min 0.751 s in 20-run set)
     - Full Boot (Create -> Guest SSH Ready): **6.846 s – 11.257 s** (20-run contention set pooled across conditions; median **8.460 s**; [boot_node_a_contention_20261114.txt:L46](file:///home/rajyavardhan/ps023/evidence/boot_node_a_contention_20261114.txt)).
     - Diagnostic Set (15 runs): **7.058 s – 16.398 s** (median **8.372 s**; [boot_node_a_bimodality_20261114.txt:L51-L54](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt)).
     - Bimodality note: Kernel boot is invariant (**327–474 ms**). Regarding the 7–16 s guest boot variance: in-guest delay during `pollinate.service` (up to 6.5 s) when querying `entropy.ubuntu.com` over bridge NAT was observed in 1 of 5 instrumented runs; cause not established; the host-contention test did not show an effect.
   - **Node B (Nested KVM)**:
     - API Create -> Status `RUNNING`: **3.222 s – 3.994 s** (5 runs; median 3.497 s)
     - Full Boot (Create -> Guest SSH Ready): **11.775 s – 19.027 s** (5 runs; median 13.130 s)
     - Evidence file: `evidence/boot_test_fallback_20261114.txt`

2. **Live Single-VM Launch**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   time curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" \
     -d "{\"name\":\"demo-live-1\",\"vcpus\":1,\"memory_mb\":512,\"target_node\":\"node-a\"}" \
     http://127.0.0.1:8000/vms | python3 -m json.tool
   '
   ```
   - Highlight: Under 1 second API response, cgroups limits calculated and applied immediately.
   - Clean up: `curl -s -X DELETE -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/vms/<VM_ID>`

---

## Act 4: High Availability Failover & Fencing (3 minutes — CENTERPIECE)

1. **Deploy HA-Protected VM on Node B**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   curl -s -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" \
     -d "{\"name\":\"ha-demo-vm\",\"vcpus\":1,\"memory_mb\":512,\"target_node\":\"node-b\",\"ha\":true}" \
     http://127.0.0.1:8000/vms | python3 -m json.tool
   '
   ```
   - Show VM running on `node-b` with IP `10.77.0.10`. Verify guest responds to SSH/ping.

2. **Simulate Catastrophic Node B Failure**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   export NODE_B_SSH_HOST=192.168.100.17
   export NODE_B_SSH_USER=rajyavardhan
   export NODE_B_SSH_PASS="$PS023_VM_PASSWORD"
   ./scripts/chaos_kill_node_b.sh worker
   '
   ```
   **What happens live**:
   - `ps023-worker` on Node B is stopped and all VMMs terminated.
   - **Total Recovery**: **14.33 s – 16.39 s** (6-run fallback repeat suite; historical Azure 6-run suite: **15.35 s – 21.05 s**, recorded over SSH tunnel).
   - **Failure Detection**: Accounts for about 14–20 s of the total (controller detects 3 consecutive missed 5-second heartbeats in **13.83 s – 15.70 s** on fallback; 15.32 s – 19.99 s on Azure).
   - **Cold Evacuation**: Accounts for about 0.4–0.7 s of the total (surviving node schedules and spawns a fresh MicroVM in **0.00 s – 0.70 s** on fallback; 0.35 s – 0.36 s on Azure).
   - IP moves to `192.168.100.10`, status returns to `RUNNING`.

3. **Restore Node B & Verify Split-Brain Fencing**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   export NODE_B_SSH_HOST=192.168.100.17
   export NODE_B_SSH_USER=rajyavardhan
   export NODE_B_SSH_PASS="$PS023_VM_PASSWORD"
   ./scripts/chaos_restore_node_b.sh worker
   '
   ```
   - Node B returns to `HEALTHY` within ~5 seconds.
   - Controller fencing pass executes: Node B reports 0 active VMs (no ghost copies running).

4. **Clean up**:
   - Delete `ha-demo-vm` via Dashboard or DELETE API.

---

## Act 5: cgroups v2 Live Memory Isolation & Host Defense (1.5 minutes)

1. **Explain the Defense-in-Depth Guarantee**:
   - Every VM is placed in a dedicated cgroup (`ps023-vmm-<vm_id>`) under `/sys/fs/cgroup`.
   - Limit = `Guest Memory + 128 MB Overhead` (for 512 MB VM, `memory.max = 671088640` bytes).
2. **Review Real Evidence (`evidence/cgroups_memory_stress_20261114.txt`)**:
   - When a guest process attempts to exceed RAM limits, the guest Linux kernel's internal OOM killer terminates the rogue process (`python3 pid 2081 killed`).
   - Host `memory.events`: `oom_kill = 0`.
   - The Cloud Hypervisor VMM process survives intact, protecting other tenants and the host operating system from denial-of-service.

---

## Act 6: Prometheus Metrics & Automated Test Suite (1.5 minutes)

1. **Prometheus Metrics Endpoint**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   curl -s -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/metrics | head -n 30
   '
   ```
   - Demonstrates production-grade Prometheus gauges (`ps023_nodes_healthy`, `ps023_node_memory_schedulable_bytes`, `ps023_vms_running`).

2. **Automated Verification**:
   ```bash
   /home/rajyavardhan/ps023/.venv/bin/pytest /home/rajyavardhan/ps023-submit/src
   ```
   - **Result**: `182 passed, 6 skipped in ~13s`.

---

## Clean Shutdown & Rollback Procedures

### Normal Teardown
```bash
# 1. Stop Controller and Workers
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8000' || true
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8001' || true

# 2. Terminate Nested Node B VMM
pkill -f 'outer.sock' || true

# 3. Verify All Listeners Closed
ss -tulpn | grep -E ':(8000|8001|8002|8012|3000)\b'
# (Expected: completely empty)
```

### Rollback to Previous Version (if needed)
```bash
rsync -ac "/home/rajyavardhan/ps023_backups/backup_20261114_190823/controller/" "/home/rajyavardhan/ps023/controller/"
rsync -ac "/home/rajyavardhan/ps023_backups/backup_20261114_190823/worker/" "/home/rajyavardhan/ps023/worker/"
```

---

## Limitations & Edge Cases to Know
1. **Hostel Wi-Fi Network Transport**: WireGuard UDP 51820 is blocked on campus Wi-Fi; all cloud benchmarks and tests use the verified SSH port-forward tunnel (`127.0.0.1:8012`).
2. **Catalog OS Images**: Alpine 3.20 and CirrOS 0.6.2 catalog entries are verified via official checksums and direct-kernel parameter specifications, but are marked "not boot-tested" pending kernel extraction.
3. **Safety Constraints**: `06-destroy-node-b.sh` must NEVER be run during demo sessions.
