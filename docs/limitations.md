# PS-023: Architectural Scope & Known Limitations

This document explicitly details the known architectural boundaries, environmental limitations, and intentional design trade-offs of the PS-023 MicroVM Orchestration Platform.

---

## 1. Authentication & Transport Security

- **Plain HTTP & Static Bearer Tokens**:
  Communication between the Controller daemon and Worker agents uses standard REST APIs over plain HTTP (`http://`), authenticated via static HTTP Bearer tokens (`Authorization: Bearer <token>`). Tokens are provisioned at bootstrap through environment variables (`PS023_API_TOKEN`, `PS023_TOKEN_NODE_A`, `PS023_TOKEN_NODE_B`).
- **No Mutual TLS (mTLS)**:
  There is no mutual certificate authority, per-node x509 certificate generation, or mTLS handshake implemented between controller and workers. In hybrid cloud deployments, transport encryption is delegated to the network layer via a WireGuard VPN tunnel (`wg0`, ChaCha20-Poly1305) or an SSH tunnel, rather than application-layer TLS.

---

## 2. Operating System & Image Catalog Scope

- **Single Boot-Tested Image (Ubuntu 24.04 LTS)**:
  Full end-to-end VM lifecycle, automated cloud-init provisioning, network configuration, and SSH readiness testing has been verified exclusively on the Ubuntu 24.04 LTS Cloud Image (`noble-server-cloudimg-amd64.raw`).
- **Catalog-Only Images (Not Boot-Tested)**:
  Other images listed in the `/images` catalog (Debian 12 Bookworm, Alpine 3.20, and CirrOS 0.6.2) are catalog entries with registered checksums and metadata, but have **not** been boot-tested or benchmarked in this test suite.

---

## 3. Host Topology & Fallback Nested Virtualization

- **Nested Node B on Single Physical Host**:
  In the primary local fallback mode, `node-b` is executed inside a nested Cloud Hypervisor Virtual Machine (`192.168.100.17`) running on the same physical host (Intel Core i7-12700H, Fedora Linux) as `node-a`.
  - While it enforces strict network boundary isolation (`10.77.0.0/24` behind `192.168.100.17` with TAP bridge routing) and independent kernel/cgroup v2 hierarchies, it shares underlying physical CPU cores, RAM, and disk bandwidth with the host.
  - Catastrophic physical host power loss would affect both nodes simultaneously in this fallback mode.
- **Azure Hybrid Node B Context**:
  Azure Node B results (`ps023-node-b`, Standard_D2s_v4 in Central India) represent recorded runs from 13–14 Nov 2026 over SSH tunnel and WireGuard. WireGuard was verified exclusively over a low-latency mobile hotspot, not over restricted hostel Wi-Fi networks (which block UDP 51820).

---

## 4. High Availability & Failure Recovery Mechanism

- **Cold Failover vs. Live Migration**:
  Failover of high-availability workloads (`ha=true`) is implemented as **cold failover**, not live memory migration.
  - **Total Recovery**: **14.33 s – 16.39 s** in fallback testing (historical Azure: **15.35 s – 21.05 s**, recorded over SSH tunnel).
  - **Failure Detection**: Accounts for about 14–20 s of total recovery (13.83 s – 15.70 s fallback; 15.32 s – 19.99 s Azure) due to three consecutive 5-second heartbeat timeouts.
  - **Cold Evacuation**: Accounts for about 0.4–0.7 s (0.00 s – 0.70 s fallback; 0.35 s – 0.36 s Azure). The controller reschedules the VM onto a surviving healthy node and executes a fresh MicroVM cold boot.
  - **Run 5 (0.00 s Evacuation)**: In fallback run 5, cold evacuation recorded 0.00 s because the controller background poll loop executed node failure detection and evacuation placement synchronously in the same tick (<0.005 s delta).
  - In-flight memory state, active TCP sockets, and non-persisted ephemeral filesystem changes on the failed node are lost upon evacuation.
- **Split-Brain Fencing**:
  When a failed node recovers, fencing is performed asynchronously by the controller's reconciliation loop: any stale Cloud Hypervisor processes matching pending tombstones or active HA VMs on other nodes are terminated via worker deletion calls. Fencing latency is typically **2.0 s – 9.33 s** post-return.
  - **Run 6 (9.33 s Fencing)**: In fallback run 6, fencing took 9.33 s post-return; the split between wait and shutdown was not instrumented.

---

## 5. Boot Performance & Telemetry Variations

- **Direct KVM Guest SSH Readiness (6.846 s to 11.257 s)**:
  While Cloud Hypervisor kernel initialization is ultra-fast and invariant (**327 ms to 474 ms**), full guest boot time (from API request to guest accepting SSH connections) on direct KVM spans **6.846 s to 11.257 s** across the 20-run contention benchmark set (median: **8.460 s**; [boot_node_a_contention_20261114.txt:L46](file:///home/rajyavardhan/ps023/evidence/boot_node_a_contention_20261114.txt)).
  - In an earlier 15-run diagnostic set ([boot_node_a_bimodality_20261114.txt:L51-L54](file:///home/rajyavardhan/ps023/evidence/boot_node_a_bimodality_20261114.txt)), outlier runs reached up to **16.398 s** (median: 8.372 s).
  - Regarding possible causes, in-guest delay during `pollinate.service` (up to 6.5 s) attempting to fetch entropy from `entropy.ubuntu.com` through NAT was observed in 1 of 5 instrumented runs; cause not established; the host-contention test did not show an effect.

---

## 6. Resource Isolation & Cgroup Limits

- **CPU & Memory Enforcement Verified**:
  MicroVM processes are successfully placed under dedicated cgroup v2 hierarchies (`ps023-vmm-<vm_id>`) with strict limits enforced:
  - `memory.max`: VM RAM + 128 MB VMM overhead.
  - `cpu.max`: vCPU quota with 1.25x burst headroom.
  - `pids.max`: 256.
- **`io.max` Block I/O Throttling Not Verified**:
  Block device I/O throttling (`io.max`) is currently **not implemented or verified**. Direct throttling of loopback/raw disk images requires device major:minor path resolution and cgroup v2 io controller support, which is not currently wired into the Cloud Hypervisor worker agent.
