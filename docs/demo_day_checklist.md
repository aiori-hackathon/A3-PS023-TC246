# PS-023: Demo Day Operational Checklist & Emergency Runbook

This checklist details the exact step-by-step procedure for the live hackathon demonstration, emergency recovery procedures, the fallback hierarchy, and quick diagnostics.

---

## 1. Pre-Demo Preparation (15 Minutes Before)

1. **Reboot Host Machine (Recommended)**:
   - Clears physical RAM, flushes dirty kernel buffers, and resets swap space.
2. **Close Heavy Desktop Applications**:
   - Close web browsers (Zen Browser, Chrome, Firefox), Discord, Slack, and heavy IDEs.
   - Target: At least **4000 MB available RAM** on host so Node A schedulable memory has plenty of headroom.
3. **Execute Pre-Flight Sanity Checker**:
   ```bash
   bash ~/ps023/scripts/demo_preflight.sh
   ```
   - **Requirement**: Must output `PRE-FLIGHT RESULT: SUCCESS (0 failures)`.
   - Verify that the line `node A schedulable memory will be about X MB` reports at least 1500–2500 MB.
4. **Prime Sudo**:
   ```bash
   sudo -v
   ```

---

## 2. Cluster Bring-Up (5 Minutes Before)

1. **Launch Automated Fallback Bring-Up**:
   ```bash
   bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
   ```
2. **Verify Output Milestones**:
   - `=== 1. host network`: bridge `br-ps023` and 8 TAP devices ready.
   - `=== 2. node-b setup`: nested VM booted and responsive at `192.168.100.17`.
   - `=== 3. node-b inner network and worker`: worker B OK.
   - `=== 4. route to the inner network`: `10.77.0.0/24 via 192.168.100.17 dev br-ps023`.
   - `=== 5. worker A and controller on the host`: worker A OK, controller OK.
   - `=== 6. cluster state`: both nodes `HEALTHY`. `READY.`
3. **Open Dashboard**:
   - Navigate to `http://127.0.0.1:8000/dashboard/`.
   - Connect using `PS023_API_TOKEN` (never speak or paste token on screen).
   - Confirm active cluster topology and healthy nodes.

---

## 3. Order of Live Demo Steps & Expected Results

Follow the verified sequence from [docs/demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md):

| Act | Step / Action | Command / UI Action | Expected Output / Result | Evidence File |
| :--- | :--- | :--- | :--- | :--- |
| **Act 1** | **Cluster Overview** | Navigate Dashboard tabs (Overview, Nodes, VMs, Decisions, Events, Images, Terminal) | 2 nodes `HEALTHY`; 7 verified views; real-time metrics | [demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md#L49-L63) |
| **Act 2** | **Scheduler Preview** | `curl -s -H "Authorization: Bearer $PS023_API_TOKEN" "http://127.0.0.1:8000/scheduler/preview?policy=best_fit&memory_mb=512"` | Packs on `node-b` (`smallest sufficient memory`); contrasts with `memory_aware` | `evidence/placement_cases_20261115.txt` |
| **Act 3** | **MicroVM Boot Speed** | POST `/vms` with `512MB` on `node-a` | API responds in **0.77 s – 1.00 s**; guest SSH ready in **6.8 s – 11.3 s** (median **8.46 s**) | `evidence/boot_node_a_contention_20261114.txt:L46` |
| **Act 4** | **HA Auto-Evacuation** | Deploy `ha=true` VM on Node B; run `./scripts/chaos_kill_node_b.sh worker` | Node B `UNHEALTHY` in ~14 s; cold evacuation to Node A in **0.00 s – 0.70 s** (total recovery **14.3 s – 16.4 s**) | `evidence/chaos_fallback_repeats_20261115.txt:L189-L194` |
| **Act 4** | **Split-Brain Fencing** | Run `./scripts/chaos_restore_node_b.sh worker` | Node B returns to `HEALTHY`; 0 duplicate VMMs running (fenced in **2.0 s – 9.3 s**) | `evidence/chaos_fallback_repeats_20261115.txt:L192-L194` |
| **Act 5** | **Cgroups Isolation** | Explain guest OOM defense in `/sys/fs/cgroup/ps023-vmm-*` | In-guest OOM killer terminates offending process; host `oom_kill = 0`; VMM unharmed | `evidence/cgroups_memory_stress_20261114.txt:L10-L71` |
| **Act 6** | **Prometheus & Tests** | `curl http://127.0.0.1:8000/metrics` and run test suite | Standard Prometheus metrics; **182 unit tests passed, 6 skipped** | `evidence/pytest-unit.txt` |

---

## 4. Fallback Ladder (Defense Hierarchy)

If any live technical dependency fluctuates, seamlessly transition down the ladder:

1. **Tier 1 (Primary Live Demo - Default)**:
   - **Local Nested Node B**: Host laptop (Node A, direct KVM) + Nested Node B (`192.168.100.17`, nested KVM) behind `br-ps023`.
   - **Advantage**: 100% local, zero reliance on external cloud or hostel Wi-Fi firewall.
2. **Tier 2 (Recorded Cloud Evidence Reference)**:
   - If questioned on multi-node / cloud deployment, present historical Azure benchmark runs recorded on 13–14 Nov 2026.
   - Show [evidence/chaos_azure_repeats_20261114.txt](file:///home/rajyavardhan/ps023/evidence/chaos_azure_repeats_20261114.txt) (6 runs over SSH tunnel; total recovery **15.35 s – 21.05 s**) and [evidence/wireguard_hotspot_20261114.txt](file:///home/rajyavardhan/ps023/evidence/wireguard_hotspot_20261114.txt) (WireGuard verified over mobile hotspot).
3. **Tier 3 (Backup Video & Automation)**:
   - **Backup Video**: Planned according to [docs/demo_shotlist.md](file:///home/rajyavardhan/ps023/docs/demo_shotlist.md) (**not recorded yet** until video is produced).
   - **Automated Rehearsal Runs**: If live execution is disrupted, present the 3 verified automated rehearsal runs ([demo_rehearsal_run1/2/3_20261115.txt](file:///home/rajyavardhan/ps023/evidence/demo_rehearsal_run1_20261115.txt)) where the entire 8-step demo completed through the REST API in **86.49 s – 91.76 s** with 0 errors.

---

## 5. Rollback Commands for Code & Disks

1. **Create Known-Good Snapshot**:
   ```bash
   # Creates ~/ps023_backups/known_good_<timestamp>/ containing controller/ and worker/
   bash ~/ps023/scripts/make_known_good_backup.sh
   ```

2. **Rollback Controller & Worker Python Code from KNOWN_GOOD (`known_good_20261115_232835`)**:
   ```bash
   # Latest verified known-good backup: /home/rajyavardhan/ps023_backups/known_good_20261115_232835
   rsync -ac "$HOME/ps023_backups/known_good_20261115_232835/controller/" "$HOME/ps023/controller/"
   rsync -ac "$HOME/ps023_backups/known_good_20261115_232835/worker/" "$HOME/ps023/worker/"
   ```
3. **Restore Nested Node B Disk Image from Verified Backup**:
   ```bash
   # Restores clean 20GB raw image with DelegateSubgroup=service & cgroups fixes applied
   cp --sparse=always /home/rajyavardhan/ps023_backups/nested_node_b_disk_20261115.raw /home/rajyavardhan/ps023/outer/disk.raw
   ```

---

## 6. "If X Breaks" Emergency Response Table

| Failure Scenario | Immediate Diagnostic | Resolution Command / Action |
| :--- | :--- | :--- |
| **1. Node A RAM drops / 409 capacity refusal** | `free -m` shows < 1500 MB available RAM | Close browser/Electron apps. Run `scripts/demo_preflight.sh` to confirm schedulable RAM > 1500 MB. |
| **2. Nested Node B unresponsive / SSH timeout** | `ping -c 2 192.168.100.17` fails | Restart outer VMM: `pkill -f 'outer.sock' && bash ~/ps023/outer/start-outer.sh &` then re-run `bring-up.sh`. |
| **3. Port conflict (8000, 8001, 8002 occupied)** | `ss -tulpn \| grep -E ':(8000\|8001\|8002)\b'` | Kill lingering instances: `pkill -f 'uvicorn.*main:app'` and check `ss -tulpn`. |
| **4. Stale cgroups / VM deletion stuck** | `find /sys/fs/cgroup -name "ps023-vmm*"` | Targeted kill by VM socket: `pkill -f "cloud-hypervisor.*api-socket.*/<vm_id>\.sock"` (or `kill -9 <PID>` from `cgroup.procs`), then remove cgroup slice. (Nested Node B outer VMM restart line stays as is: `pkill -f 'outer.sock'`). |
| **5. Live demo HA evacuation stalls** | Evacuation exceeds 30 seconds | Fall back immediately to Tier 2: open and present raw data in `evidence/chaos_fallback_repeats_20261115.txt`. |
