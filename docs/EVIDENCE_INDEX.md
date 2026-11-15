# PS-023: Comprehensive Evidence & Verification Index

This index maps every performance claim, benchmark figure, and operational metric in the PS-023 platform directly to its source evidence file and line range. Any parameter or metric not directly measured in testing is explicitly labeled as **"not measured"**.

---

## 1. MicroVM Boot Latency & Launch Performance

| Metric / Claim | Measured Value / Range | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Node A Kernel Initialization** | 327 ms – 474 ms | [boot_node_a_bimodality_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt) | L33–L46, L59 | **VERIFIED** |
| **Node A API Create -> Status RUNNING** | 0.772 s – 0.997 s (Min: 0.751 s in 20-run set) | [boot_node_a_bimodality_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt) | L13–L27 | **VERIFIED** |
| **Node A Full Boot (Primary 20-Run Contention Set)** | Min: 6.846 s, Median: 8.460 s, Max: 11.257 s | [boot_node_a_contention_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_contention_20261114.txt) | L45–L48 | **VERIFIED** |
| **Node A Full Boot (Diagnostic 15-Run Bimodality Set)** | Min: 7.058 s, Median: 8.372 s, Max: 16.398 s (pollinate delay observed in 1 of 5 instrumented runs; cause not established; host-contention test did not show an effect) | [boot_node_a_bimodality_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt) | L49–L55 | **VERIFIED** |
| **Node B Nested API Create -> Status RUNNING** | 3.222 s – 3.994 s (median 3.497 s) | [boot_test_fallback_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt) | L41–L45 | **VERIFIED** |
| **Node B Nested Full Boot (API -> SSH Ready)** | 11.775 s – 19.027 s (median 13.130 s) | [boot_test_fallback_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt) | L46–L50 | **VERIFIED** |
| **Azure Node B Boot Speed** | *Not measured separately from Azure chaos runs* | — | — | **Not measured** |

---

## 2. High Availability Failover & Split-Brain Fencing

### A. Local Fallback Environment (Nested Node B on 192.168.100.17 - 15 Nov 2026)
Source: [chaos_fallback_repeats_20261115.txt](file:///home/rajyavardhan/ps023/evidence/chaos_fallback_repeats_20261115.txt)

| Run | Chaos Mode | Detection Delay (s) | Cold Evac Latency (s) | Total Recovery (s) | Split-Brain Fencing Outcome | Line(s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | `worker` | 14.61 s | 0.51 s | 15.12 s | CLEAN (0 stale VMMs) | L189 |
| **Run 2** | `worker` | 14.79 s | 0.51 s | 15.30 s | CLEAN (0 stale VMMs) | L190 |
| **Run 3** | `worker` | 14.20 s | 0.51 s | 14.71 s | CLEAN (0 stale VMMs) | L191 |
| **Run 4** | `worker-preserve-vms` | 13.83 s | 0.51 s | 14.33 s | KILLED (2.0s post-return) | L192 |
| **Run 5** | `worker-preserve-vms` | 14.74 s | 0.00 s | 14.74 s | KILLED (6.75s post-return) | L193 |
| **Run 6** | `worker-preserve-vms` | 15.70 s | 0.70 s | 16.39 s | KILLED (9.33s post-return) | L194 |

*Note on Run 5 (0.00 s Evacuation)*: The controller background polling loop executed node failure detection and evacuation placement synchronously in the same tick (<0.005 s delta).  
*Note on Run 6 (9.33 s Fencing)*: Fencing of the stale VMM was verified at 9.33 s post-return; the split between wait and shutdown was not instrumented.

### B. Azure Hybrid Cloud Environment (Historical Recorded Runs, 13–14 Nov 2026)
Source: [chaos_azure_repeats_20261114.txt](file:///home/rajyavardhan/ps023/evidence/chaos_azure_repeats_20261114.txt) (Transport: SSH tunnel / sshuttle)

| Run | Chaos Mode | Detection Delay (s) | Cold Evac Latency (s) | Total Recovery (s) | Outcome | Line(s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | `worker` | 15.32 s | 0.36 s | 15.35 s | Evacuated to RUNNING | L402 |
| **Run 2** | `worker` | 19.99 s | 0.36 s | 21.05 s | Evacuated to RUNNING | L403 |
| **Run 3** | `worker` | 17.16 s | 0.36 s | 18.22 s | Evacuated to RUNNING | L404 |
| **Run 4** | `worker-preserve-vms` | 17.44 s | 0.35 s | 18.50 s | Evacuated to RUNNING | L405 |
| **Run 5** | `worker-preserve-vms` | 18.60 s | 0.36 s | 18.63 s | Evacuated to RUNNING | L406 |
| **Run 6** | `worker-preserve-vms` | 15.92 s | 0.36 s | 15.97 s | Evacuated to RUNNING | L407 |

*Note on Azure Suite*: Total recovery ranges from **15.35 s to 21.05 s**. Detection is 15.32 s – 19.99 s (~15–20 s of total), and cold evacuation is 0.35 s – 0.36 s.

---

## 3. Controller Fault-Tolerance & Reconciliation

| Metric / Scenario | Measured Value / Result | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Controller Service Restart Latency** | 2.06 s | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L22 | **VERIFIED** |
| **Pre-Restart VM Preservation** | 2 of 2 VMs preserved in `RUNNING` status | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L28–L30 | **VERIFIED** |
| **Duplicate / Orphan Detection** | 0 duplicates, 0 orphans post-reconciliation | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L32 | **VERIFIED** |

---

## 4. Resource Isolation & Cgroup v2 Enforcement

| Feature / Limit | Enforcement Result | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`memory.max` Boundary** | `VM_RAM + 128MB overhead` (640MB for 512MB guest). In-guest kernel OOM-kills rogue task before host limit breached; VMM process unharmed | [cgroups_memory_stress_20261114.txt](file:///home/rajyavardhan/ps023/evidence/cgroups_memory_stress_20261114.txt) | L10–L12, L40–L42, L65–L71 | **VERIFIED** |
| **`cpu.max` Quota** | CFS bandwidth configured with 1.25x burst headroom (125000 / 100000) | [cgroups_memory_stress_20261114.txt](file:///home/rajyavardhan/ps023/evidence/cgroups_memory_stress_20261114.txt) | L13–L15 | **VERIFIED** |
| **`pids.max` Limit** | Configured to 256 in code (`worker/cgroup_manager.py:L120`); limit boundary stress test not run | [cgroup_manager.py](file:///home/rajyavardhan/ps023/worker/cgroup_manager.py#L120) | L120 | **Not measured** |
| **`io.max` Throttling** | *Not implemented / not wired to VMM* | [limitations.md](file:///home/rajyavardhan/ps023/docs/limitations.md) | Sec 6 | **Not measured** |

---

## 5. API Placement & Error Handling

| Scenario | API Response & Behavior | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Insufficient Capacity (Cluster Overload)** | HTTP 409 with structured candidate reasons (`node-a: skipped`, `node-b: skipped`) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L11–L41 | **VERIFIED** |
| **Unknown Target Node Pinning** | HTTP 422 Unprocessable Entity (`unknown target_node '...'`) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L44–L52 | **VERIFIED** |
| **Capacity Refusal Fall-Through** | Scheduler bypassed `node-a` (2045 MB < 2301 MB) and placed automatically on `node-b` (2549 MB) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L55–L62 | **VERIFIED** |

---

## 6. Networking & Transport Verification

| Transport Layer | Measured Latency / Behavior | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Local Bridge (`br-ps023`) Routing** | Direct subnet routing `10.77.0.0/24` via `192.168.100.17` | [demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md) | L31–L32 | **VERIFIED** |
| **WireGuard Handshake (Mobile Hotspot)** | Successful bidirectional handshake (1.78 KiB recv, 1.91 KiB sent) | [wireguard_hotspot_20261114.txt](file:///home/rajyavardhan/ps023/evidence/wireguard_hotspot_20261114.txt) | L22–L28, L35–L40 | **VERIFIED** |
| **WireGuard Raw Ping RTT (Mobile Hotspot)** | Node A -> Node B: `rtt min/avg/max/mdev = 76.865/154.511/215.156/61.235 ms`<br>Node B -> Node A: `rtt min/avg/max/mdev = 68.312/189.759/473.877/167.117 ms`<br>*(Earlier interactive pre-test on 14 Nov logged: A->B 441.368 ms avg; B->A 134.855 ms avg)* | [wireguard_hotspot_20261114.txt](file:///home/rajyavardhan/ps023/evidence/wireguard_hotspot_20261114.txt) | L49–L52, L60–L63 | **VERIFIED** |
| **WireGuard on Hostel Wi-Fi** | Blocked by local network UDP 51820 firewall filter | [wireguard_hotspot_20261114.txt](file:///home/rajyavardhan/ps023/evidence/wireguard_hotspot_20261114.txt)<br>[demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md) | L75–L80<br>L6 | **VERIFIED BLOCKED** |
| **Network Throughput / Bandwidth** | *Not measured* | — | — | **Not measured** |

---

## 7. Automated End-to-End Demo Rehearsals

Source scripts: `scripts/demo_rehearsal.py` (executing all 8 demo flow acts sequentially via REST API)

| Rehearsal Run | Date & Time | Duration | Outcome | Evidence File | Line(s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | 2026-11-15 13:59:17 IST | 86.49 s | SUCCESS (All 8 steps passed, 0 errors) | [demo_rehearsal_run1_20261115.txt](file:///home/rajyavardhan/ps023/evidence/demo_rehearsal_run1_20261115.txt) | L60–L76 |
| **Run 2** | 2026-11-15 14:02:45 IST | 91.76 s | SUCCESS (All 8 steps passed, 0 errors) | [demo_rehearsal_run2_20261115.txt](file:///home/rajyavardhan/ps023/evidence/demo_rehearsal_run2_20261115.txt) | L60–L76 |
| **Run 3** | 2026-11-15 14:05:30 IST | 91.53 s | SUCCESS (All 8 steps passed, 0 errors) | [demo_rehearsal_run3_20261115.txt](file:///home/rajyavardhan/ps023/evidence/demo_rehearsal_run3_20261115.txt) | L60–L76 |
