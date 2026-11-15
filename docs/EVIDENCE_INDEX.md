# PS-023: Comprehensive Evidence & Verification Index

This index maps every performance claim, benchmark figure, and operational metric in the PS-023 platform directly to its source evidence file and line range. Any parameter or metric not directly measured in testing is explicitly labeled as **"not measured"**.

---

## 1. MicroVM Boot Latency & Launch Performance

| Metric / Claim | Measured Value / Range | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Node A Kernel Initialization** | 327 ms – 474 ms | [boot_test_fallback_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt) | L15–L25 | **VERIFIED** |
| **Node A API Create -> Status RUNNING** | 0.772 s – 0.997 s | [boot_node_a_bimodality_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt) | L35–L52 | **VERIFIED** |
| **Node A Full Boot (API -> SSH Ready, 15 pooled runs)** | Min: 7.058 s, Median: 8.372 s, Max: 16.398 s | [boot_node_a_bimodality_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt) | L10–L65 | **VERIFIED** |
| **Node A Boot Under Contention (5 concurrent VMs)** | 8.878 s – 11.233 s | [boot_node_a_contention_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_node_a_contention_20261114.txt) | L45–L80 | **VERIFIED** |
| **Node B Nested API Create -> Status RUNNING** | 3.222 s – 3.994 s (median 3.497 s) | [boot_test_fallback_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt) | L55–L85 | **VERIFIED** |
| **Node B Nested Full Boot (API -> SSH Ready)** | 11.775 s – 19.027 s (median 13.130 s) | [boot_test_fallback_20261114.txt](file:///home/rajyavardhan/ps023/evidence/boot_test_fallback_20261114.txt) | L55–L85 | **VERIFIED** |
| **Azure Node B Boot Speed** | *Not measured separately from Azure chaos runs* | — | — | **Not measured** |

---

## 2. High Availability Failover & Split-Brain Fencing

### A. Local Fallback Environment (Nested Node B on 192.168.100.17 - 15 Nov 2026)
Source: [chaos_fallback_repeats_20261115.txt](file:///home/rajyavardhan/ps023/evidence/chaos_fallback_repeats_20261115.txt)

| Run | Chaos Mode | Detection Delay (s) | Cold Evac Latency (s) | Total Recovery (s) | Split-Brain Fencing Outcome | Line(s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | `worker` | 14.61 s | 0.51 s | 15.12 s | CLEAN (0 stale VMMs) | L231 |
| **Run 2** | `worker` | 14.79 s | 0.51 s | 15.30 s | CLEAN (0 stale VMMs) | L232 |
| **Run 3** | `worker` | 14.20 s | 0.51 s | 14.71 s | CLEAN (0 stale VMMs) | L233 |
| **Run 4** | `worker-preserve-vms` | 13.83 s | 0.51 s | 14.33 s | KILLED (2.00 s post-return) | L234 |
| **Run 5** | `worker-preserve-vms` | 14.74 s | 0.00 s | 14.74 s | KILLED (6.75 s post-return) | L235 |
| **Run 6** | `worker-preserve-vms` | 15.70 s | 0.70 s | 16.39 s | KILLED (9.33 s post-return) | L236 |

### B. Azure Hybrid Cloud Environment (Recorded 13–14 Nov 2026)
Source: [chaos_azure_repeats_20261114.txt](file:///home/rajyavardhan/ps023/evidence/chaos_azure_repeats_20261114.txt)

| Run | Transport Mode | Detection Delay (s) | Cold Evac Latency (s) | Total Recovery (s) | Fencing Outcome | Line(s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | SSH-Tunnel | 14.00 s | 0.42 s | 14.42 s | CLEAN (0 stale VMMs) | L185–L190 |
| **Run 2** | SSH-Tunnel | 14.88 s | 0.58 s | 15.46 s | CLEAN (0 stale VMMs) | L191–L195 |
| **Run 3** | SSH-Tunnel | 14.20 s | 0.45 s | 14.65 s | CLEAN (0 stale VMMs) | L196–L200 |
| **Run 4** | WireGuard (Mobile Hotspot) | 14.15 s | 0.50 s | 14.65 s | CLEAN (0 stale VMMs) | L201–L205 |

---

## 3. Controller Fault-Tolerance & Reconciliation

| Metric / Scenario | Measured Value / Result | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Controller Service Restart Latency** | 2.06 s | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L31 | **VERIFIED** |
| **Pre-Restart VM Preservation** | 2 of 2 VMs preserved in `RUNNING` status | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L41–L45 | **VERIFIED** |
| **Duplicate / Orphan Detection** | 0 duplicates, 0 orphans post-reconciliation | [controller_restart_20261115.txt](file:///home/rajyavardhan/ps023/evidence/controller_restart_20261115.txt) | L46–L47 | **VERIFIED** |

---

## 4. Resource Isolation & Cgroup v2 Enforcement

| Feature / Limit | Enforcement Result | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`memory.max` Boundary** | Worker calculates `VM_RAM + 128MB overhead`; OOM killer terminates over-consuming process | [cgroups_memory_stress_20261114.txt](file:///home/rajyavardhan/ps023/evidence/cgroups_memory_stress_20261114.txt) | L30–L65 | **VERIFIED** |
| **`cpu.max` Quota** | CFS bandwidth enforced with 1.25x burst headroom | [cgroups_memory_stress_20261114.txt](file:///home/rajyavardhan/ps023/evidence/cgroups_memory_stress_20261114.txt) | L70–L95 | **VERIFIED** |
| **`pids.max` Limit** | Enforced at 256 PIDs per MicroVM unit | [cgroups_memory_stress_20261114.txt](file:///home/rajyavardhan/ps023/evidence/cgroups_memory_stress_20261114.txt) | L100–L110 | **VERIFIED** |
| **`io.max` Throttling** | *Not implemented / not wired to VMM* | [limitations.md](file:///home/rajyavardhan/ps023/docs/limitations.md) | Sec 6 | **Not measured** |

---

## 5. API Placement & Error Handling

| Scenario | API Response & Behavior | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Insufficient Capacity (Cluster Overload)** | HTTP 409 with structured candidate reasons (`node-a: skipped`, `node-b: skipped`) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L20–L45 | **VERIFIED** |
| **Unknown Target Node Pinning** | HTTP 422 Unprocessable Entity (`unknown target_node '...'`) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L50–L65 | **VERIFIED** |
| **Capacity Refusal Fall-Through** | Scheduler bypassed `node-a` (2045 MB < 2301 MB) and placed automatically on `node-b` (2549 MB) | [placement_cases_20261115.txt](file:///home/rajyavardhan/ps023/evidence/placement_cases_20261115.txt) | L70–L90 | **VERIFIED** |

---

## 6. Networking & Transport Verification

| Transport Layer | Measured Latency / Behavior | Evidence File | Line(s) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Local Bridge (`br-ps023`) Routing** | Direct subnet routing `10.77.0.0/24` via `192.168.100.17` | [demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md) | L31–L32 | **VERIFIED** |
| **WireGuard Handshake (Mobile Hotspot)** | Successful handshake, RTT ~38 ms | [wireguard_hotspot_20261114.txt](file:///home/rajyavardhan/ps023/evidence/wireguard_hotspot_20261114.txt) | L22–L35 | **VERIFIED** |
| **WireGuard on Hostel Wi-Fi** | *Blocked by local network UDP filter* | [demo-script.md](file:///home/rajyavardhan/ps023/docs/demo-script.md) | L6 | **VERIFIED BLOCKED** |
| **Network Throughput / Bandwidth** | *Not measured* | — | — | **Not measured** |
