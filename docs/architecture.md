# PS-023: System Architecture Specification

## 1. Executive Overview

PS-023 is a lightweight, distributed MicroVM orchestration platform designed for Cloud Hypervisor on Linux with cgroups v2 resource guarantees. The platform enables multi-tenant virtual machine lifecycle management, pluggable policy scheduling, real-time in-browser terminal access, and automated cold failover (14.3 s – 16.4 s total recovery, 0.00 s – 0.70 s cold evacuation on surviving node) across heterogeneous compute infrastructure.

---

## 2. Target Environments & Demonstration Topology

### A. Primary Demonstration Environment (Local Fallback Mode)
- **Node A (Host)**: Direct hardware KVM virtualization on Fedora Linux (`127.0.0.1:8001`), Intel Core i7-12700H (12 vCPUs, 15 GB RAM). IP subnet `192.168.100.0/24`.
- **Node B (Nested Compute)**: Fully isolated nested Cloud Hypervisor instance on `192.168.100.17:8002` (4 vCPUs, 4 GB RAM) managing inner guests in `10.77.0.0/24` with TAP bridge routing (`br-ps023`).
- **Rationale**: Provides 100% reliable hardware virtualization demonstrations with zero dependency on external cloud networks or hotel/hostel Wi-Fi restrictions.

### B. Azure Hybrid Cloud Environment (Reference Runs: 13–14 Nov 2026)
- **Node B (Cloud)**: Azure `Standard_D2s_v4` in Central India (`10.100.0.2:8002`, 2 vCPU / 8 GiB).
- **Transport Modes Evaluated**:
  - `ssh-tunnel`: Verified on 13–14 Nov 2026.
  - `wireguard`: Verified exclusively over a dedicated mobile hotspot (UDP 51820). Note: Local venue hostel Wi-Fi firewalls block UDP 51820.

---

## 3. Core Architectural Subsystems

### 1. Central Controller Daemon (`ps023-controller`)
- **FastAPI / Uvicorn Service** listening on port 8000.
- **State Store**: SQLite in Write-Ahead Logging (WAL) mode.
- **Heartbeat Monitor**: Periodic 5-second polling of node `/health` endpoints. Declares node `UNHEALTHY` after 3 consecutive failures (~14–15 s).
- **Reconciliation Engine**: Decoupled state reconciler that detects recovering nodes, fences duplicate stale VMMs, cleans tombstones, and ensures 0-orphan controller restart tolerance.

### 2. Worker Node Agent (`ps023-worker`)
- Runs as a systemd unit (`ps023-worker.service`) on each compute node.
- Spawns and manages Cloud Hypervisor processes via their local Unix domain socket APIs (`/api/v1`).
- Enforces systemd `Delegate=yes`, `DelegateSubgroup=service`, and `KillMode=process` to guarantee that worker daemon restarts never conflict with running MicroVM cgroups under cgroup v2.

### 3. Pluggable Scheduler
- **`memory_aware`**: Selects node with highest absolute available RAM (default for multi-tenant load balancing).
- **`best_fit`**: Selects node with smallest sufficient RAM (density packing).
- **`first_fit`**: Selects first node meeting capacity requirements.
- **API Preview**: `/scheduler/preview` exposes live placement reasoning across all policies simultaneously.

### 4. High-Availability Auto-Evacuation
- Automatically respawns `ha=true` MicroVMs when their host node fails.
- **Total Recovery**: **14.33 s – 16.39 s** on fallback (Azure historical: **15.35 s – 21.05 s**, recorded over SSH tunnel).
- **Failure Detection**: Accounts for about 14–20 s (13.83 s – 15.70 s fallback; 15.32 s – 19.99 s Azure).
- **Cold Evacuation**: Accounts for about 0.4–0.7 s (0.00 s – 0.70 s fallback; 0.35 s – 0.36 s Azure) on the surviving node.
- When failed node rejoins, split-brain fencing pass terminates stale copies within **2.0 s – 9.33 s** post-return.
