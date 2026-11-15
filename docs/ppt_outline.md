# PS-023: Hackathon Presentation Deck Outline & Jury Defense Guide
**Standard Format**: AIORI Hackathon Structure (`Proposed-structure-hackathon.pdf`)  
**Target Environment**: Primary Local Fallback (Direct KVM Node A + Nested KVM Node B) & Azure Hybrid Reference  
**Deck Generation Status**: `python-pptx` is **not installed** in this environment (`ModuleNotFoundError: No module named 'pptx'`); complete presentation markdown, diagram sources, data tables, and slide contents are fully rendered below for slide authoring.

---

## Slide 1: Title Slide
- **Title**: PS-023: High-Availability Cloud Hypervisor MicroVM Orchestration Platform
- **Subtitle**: Sub-Second Cold Failover, Cgroups v2 Isolation & Pluggable Policy Scheduling across Heterogeneous Infrastructure
- **Presenter**: Rajyavardhan
- **Event**: AIORI Hackathon 3
- **Date**: November 15, 2026
- **Architecture Tag**: Direct KVM / Heterogeneous Hybrid Linux Cloud

---

## Slide 2: Problem Description
- **Key Issues Addressed**:
  - **Virtualization Bloat & Slow Boot**: Traditional QEMU/KVM hypervisors carry massive legacy device emulation, resulting in multi-minute cold boot times and heavyweight resource footprints (500MB+ per guest overhead).
  - **Noisy Neighbor Contention**: In multitenant edge/cloud environments, uncontrolled microVM processes can starve host memory and CPU CFS shares, triggering cascading host OOM kills.
  - **Catastrophic Worker Failure & Brain-Split**: When an edge compute node abruptly crashes or loses network connectivity, orchestrators often take minutes to detect failure, or risk split-brain dual-primary corruption upon node recovery.
  - **Rigid Scheduling**: Monolithic cloud schedulers cannot adapt dynamically between density packing (`best_fit`) and latency-sensitive distribution (`memory_aware`) across asymmetric hardware.

---

## Slide 3: Background
- **Context & Optimization Goals**:
  - Modern edge computing demands lightweight hardware virtualization with minimal overhead (Rust-based Cloud Hypervisor).
  - High availability requires real-time heartbeat monitoring with sub-second evacuation rather than manual operator intervention.
  - Control plane reliability necessitates stateful database reconciliation where controller restarts preserve in-flight guests with zero orphan processes.

---

## Slide 4: Literature & RFC Review
- **Standards & Prior Art**:
  - **Linux Cgroups v2 Unified Hierarchy** (Linux Kernel Documentation): Single unified control tree eliminating v1 controller synchronization races.
  - **Rust-vmm / Cloud Hypervisor Project**: Low-overhead VMM focusing on modern virtio devices and direct kernel boot without legacy PCI/BIOS overhead.
  - **RFC 793 / TCP & WireGuard Protocol** (Donenfeld, 2017): Kernel-space ChaCha20-Poly1305 encapsulated tunneling for secure node-to-node overlay networks.
  - **Split-Brain Mitigation in Distributed Quorums**: Fencing tokens and state tombstones ensuring recovering nodes purge superseded execution units.

---

## Slide 5: Proposed Solution
- **Core Architecture Components**:
  - **Central Orchestrator (Controller)**: FastAPI/Uvicorn control plane maintaining cluster state in SQLite with WAL mode, background heartbeat monitor (5s lease), pluggable scheduling engine, and automatic tombstone reconciler.
  - **Node Agent (Worker Daemon)**: REST API service running per compute node, spawning Cloud Hypervisor VMM instances, managing network TAP interfaces, and binding guests into delegated cgroup v2 subgroups.
  - **Dynamic In-Browser WebSocket Terminal**: Real-time interactive PTY console without opening SSH ports to the public internet.

---

## Slide 6: Optimization Proposed
- **Comparison of Before & After Capabilities**:

| Capability / Metric | Traditional VM Orchestrator | PS-023 Cloud Hypervisor Platform | Evidence Reference |
| :--- | :--- | :--- | :--- |
| **VMM Memory Overhead** | 256 MB – 1024 MB | **128 MB fixed overhead** (enforced via cgroups) | `cgroups_memory_stress_20261114.txt` |
| **Kernel Boot Duration** | 2.5 s – 8.0 s | **327 ms – 474 ms** (Node A direct KVM) | `boot_test_fallback_20261114.txt:L15` |
| **API Create -> Running** | 5.0 s – 15.0 s | **0.772 s – 0.997 s** | `boot_node_a_bimodality_20261114.txt:L35` |
| **HA Failure Detection** | 30 s – 120 s (timeout loops) | **13.83 s – 15.70 s** (fallback) / **14.0 s – 14.88 s** (Azure) | `chaos_fallback_repeats_20261115.txt` |
| **Cold Evacuation Latency** | 10 s – 45 s | **0.00 s – 0.70 s** (sub-second cold failover) | `chaos_fallback_repeats_20261115.txt` |
| **Total Failover Recovery** | 45 s – 180 s | **14.33 s – 16.39 s** (complete recovery) | `chaos_fallback_repeats_20261115.txt` |
| **Split-Brain Fencing** | Manual reboot / IPMI STONITH | **Automated worker reconciliation (2.0s – 9.33s)** | `chaos_fallback_repeats_20261115.txt` |

---

## Slide 7: Solution Architecture & Sequence Flows

### 1. High-Level Cluster Architecture
```mermaid
graph TB
    subgraph Host["Host Machine (Intel Core i7-12700H / Fedora)"]
        UI["React Dashboard (:3000 / :8000)"] --> Ctrl["PS-023 Controller (:8000)"]
        Ctrl --> DB[("SQLite Database (WAL)")]
        Ctrl -->|HTTP / Token| WorkerA["Worker A (:8001)"]
        
        subgraph NodeA["Compute Node A (Local KVM)"]
            WorkerA --> VMM_A["Cloud Hypervisor VMMs"]
            VMM_A --> CG_A["/sys/fs/cgroup/ps023-vmm-*"]
            VMM_A --> NetA["TAP Interfaces (192.168.100.x)"]
        end

        subgraph NodeB_Fallback["Compute Node B (Nested KVM : 192.168.100.17)"]
            Ctrl -->|Bridge Route 10.77.0.0/24| WorkerB["Worker B (:8002)"]
            WorkerB --> VMM_B["Nested Cloud Hypervisor VMMs"]
            VMM_B --> CG_B["Delegated cgroup v2 /service"]
        end
    end
```

### 2. MicroVM Placement Flow
```mermaid
flowchart TD
    Req["POST /vms Request (memory_mb, vcpus, target_node)"] --> Validate{"target_node pinned?"}
    Validate -- Yes --> CheckPin{"Pinned node healthy & sufficient RAM?"}
    CheckPin -- Yes --> WorkerPost["Call Worker POST /vms"]
    CheckPin -- No (Unknown) --> R422["HTTP 422: unknown target_node"]
    CheckPin -- No (Oversized) --> R409["HTTP 409: insufficient memory"]
    
    Validate -- No (Auto) --> PolEval["Evaluate Scheduler Policies (memory_aware, best_fit, first_fit)"]
    PolEval --> FitCheck{"Any node fits memory_mb?"}
    FitCheck -- No --> R409
    FitCheck -- Yes --> SelectNode["Select Candidate Node"]
    SelectNode --> WorkerPost
    WorkerPost --> WorkerCheck{"Worker returns 409?"}
    WorkerCheck -- Yes (Refusal) --> Fallthrough["Fall through to next candidate node"]
    Fallthrough --> WorkerPost
    WorkerCheck -- No (201 Created) --> Success["Update DB & Return VM Details"]
```

### 3. Stop Escalation & Failover Sequence
```mermaid
sequenceDiagram
    autonumber
    participant U as User / Operator
    participant C as Controller
    participant WA as Worker A (Surviving)
    participant WB as Worker B (Failed)
    participant VMM as Cloud Hypervisor

    Note over U,VMM: MicroVM Stop Escalation
    U->>C: POST /vms/{id}/stop
    C->>WA: POST /vms/{id}/stop
    WA->>VMM: ACPI Power Button
    alt Guest shuts down gracefully (<30s)
        VMM-->>WA: Process Exits
    else Timeout (30s elapsed)
        WA->>VMM: SIGTERM (vmm_shutdown)
        WA->>VMM: SIGKILL (kill -9 fallback)
    end
    WA-->>C: Status STOPPED & Cgroups Cleaned

    Note over U,VMM: Chaos Failure & Self-Healing Evacuation
    WB-xWB: Worker Crash / Process Killed
    loop Heartbeat Check (every 5s)
        C->>WB: GET /health
        WB--xC: Connection Refused / Timeout
    end
    C->>C: 3 Consec Timeouts (~14s) -> Mark Node B UNHEALTHY
    C->>C: Evacuation Reconciler Triggers
    C->>WA: POST /vms (Create Evacuated VM on Node A)
    WA-->>C: 201 Created (Evacuated in 0.51s, Status RUNNING)
    
    Note over U,VMM: Recovery & Split-Brain Fencing
    WB->>WB: Worker B Restarts (systemctl start)
    C->>WB: GET /health -> Node B HEALTHY
    C->>WB: Reconciliation: Delete Stale Tombstones / Duplicate HA VMs
    WB->>VMM: Terminate Stale VMM Process (Fenced in 2.0s - 9.3s)
```

---

## Slide 8: Data Flow Diagram (DFD)
```mermaid
graph LR
    Client["User / Web Browser"] -->|HTTP REST / WebSocket| API["FastAPI Gateway"]
    API -->|Read / Write| DB[("SQLite DB")]
    API -->|Dispatch| Core["VM Service Engine"]
    Core -->|Placement Query| Sched["Pluggable Scheduler"]
    Sched -->|Node State| DB
    Core -->|HTTP Bearer| WC["Worker Client"]
    WC -->|Direct TAP / WireGuard| W_Daemon["Remote Worker Daemon"]
    W_Daemon -->|Unix Domain Socket| CH_API["Cloud Hypervisor /api/v1"]
    W_Daemon -->|fs write| CGROUP["/sys/fs/cgroup/"]
```

---

## Slide 9: Deployment Timeline & Milestones
- **Phase 1: Architecture & Hypervisor Foundation (Oct 2026)**
  - Cloud Hypervisor API integration, TAP network bridge, cloud-init automated provisioning.
- **Phase 2: Pluggable Scheduling & Cgroups v2 Enforcement (Early Nov 2026)**
  - Development of `memory_aware`, `best_fit`, and `first_fit` algorithms; strict memory overhead, CPU CFS quota, and PID isolation.
- **Phase 3: High Availability, Failover & Split-Brain Fencing (12–14 Nov 2026)**
  - Auto-evacuation engine, tombstone tracking, Azure hybrid cloud WireGuard and SSH-tunnel integration.
- **Phase 4: Fallback Hardening, Benchmarking & Rehearsal (15 Nov 2026)**
  - 6-run fallback chaos repeat suite, systemd `DelegateSubgroup=service` cgroup restart resolution, controller restart reconciliation, and rehearsal automation.

---

## Slide 10: Known Limitations Slide
*(Mandatory Engineering Transparency)*
- **Plain HTTP & Bearer Auth**: No mutual TLS (mTLS); transport security relies on network overlays (WireGuard/SSH).
- **Single Tested Distribution**: Ubuntu 24.04 LTS is the sole boot-tested OS; Debian, Alpine, and CirrOS remain catalog-only entries.
- **Local Fallback Shared Hardware**: Nested Node B runs on the same physical CPU/RAM/motherboard as Node A.
- **Cold Evacuation, Not Live Migration**: Workloads restart from clean disk; in-memory state is not preserved during failover.
- **Boot Time Variance (7.058 s to 16.398 s)**: Invariant kernel boot (~350 ms), but in-guest cloud-init/pollinate network entropy fetch causes bimodal variance.
- **Block I/O (`io.max`) Not Enforced**: Only CPU quota, memory max, and PID limits are currently verified.

---

## Slide 11: Summary & Conclusion
- **Delivered Capabilities**:
  - Sub-second MicroVM placement and cold evacuation (**0.00 s – 0.70 s**).
  - Robust split-brain fencing eliminating duplicate primary execution units.
  - Zero-orphan controller restart reconciliation in **2.06 s**.
  - Production-grade cgroup v2 resource guarantees preventing host denial of service.

---

## Appendix: Jury Defense Cheat Sheet & Real Evidence Cross-Reference

| Likely Jury Question | Authoritative Technical Answer | Source Evidence File |
| :--- | :--- | :--- |
| **Q1: "How fast is cold boot really, and why does it vary from 7s to 16s?"** | Cloud Hypervisor kernel boot is invariant at **327–474 ms**. The variance between 7s and 16s occurs entirely inside the guest operating system during systemd boot (specifically `pollinate.service` querying `entropy.ubuntu.com` over NAT). | `evidence/boot_test_fallback_20261114.txt:L15`<br>`evidence/boot_node_a_bimodality_20261114.txt:L10-L65` |
| **Q2: "What happens if a failed node comes back online while its VM was evacuated elsewhere?"** | The split-brain fencing mechanism in `reconcile.py` cross-checks active HA VMs against tombstone records. Upon Node B's return, the controller immediately instructs Node B's worker to terminate any duplicate stale VMM processes (**fenced in 2.0s to 9.33s**). | `evidence/chaos_fallback_repeats_20261115.txt:L230-L245` |
| **Q3: "If the controller crashes, do running MicroVMs get killed?"** | No. Worker daemons and Cloud Hypervisor processes operate independently of the controller. When the controller restarts (taking **2.06 s**), the reconciliation loop discovers existing running VMs via `/vms` on each worker, re-syncs state with 0 orphans and 0 duplicates. | `evidence/controller_restart_20261115.txt:L1-L60` |
| **Q4: "How do you prevent a runaway VM from taking down the host?"** | Each MicroVM is placed in a cgroup v2 slice with hard `memory.max` (`VM_RAM + 128MB`), `cpu.max` (vCPU CFS quota with 1.25x headroom), and `pids.max` (256). Stress tests confirm host kernel OOM-kills the offending guest process without affecting other VMs or the host. | `evidence/cgroups_memory_stress_20261114.txt:L30-L100` |
| **Q5: "How does the scheduler handle edge cases like capacity refusal?"** | If a request exceeds cluster memory, the API returns **HTTP 409** with structured per-node candidate rejection reasons. If pinned to an invalid node, it returns **HTTP 422**. If an unpinned request fits only on a specific node, it automatically falls through. | `evidence/placement_cases_20261115.txt:L1-L90` |
| **Q6: "Why is local fallback used instead of Azure for today's presentation?"** | Azure hybrid mode was benchmarked on 13–14 Nov over WireGuard and SSH tunnel. However, local venue hostel Wi-Fi enforces strict UDP firewall filters that block WireGuard (UDP 51820). The local fallback architecture provides identical KVM isolation and subnet routing reliably without external network dependencies. | `evidence/wireguard_hotspot_20261114.txt`<br>`evidence/chaos_azure_repeats_20261114.txt` |
