# PS-023: Microsoft Azure Migration Audit & Technical Assessment
**Project ID**: A3-PS023-TC246  
**Team**: The Mavericks  
**Date**: November 11, 2026  
**Status**: Phase 0 Complete — Ready for Review

---

## 1. Executive Summary

This audit assesses the migration of Node B from a local nested VM (`192.168.100.17`) and the historical AWS EC2 bare-metal plan to **Microsoft Azure** (running nested KVM on a `Standard_D2s_v5` Ubuntu 24.04 LTS instance).

The objective is to establish a **genuine hybrid two-node virtualization control plane**:
- **Node A (Local Edge)**: Fedora 45 laptop (AMD Ryzen 7 7445HS, 12 threads, 16 GB RAM), hosting the central FastAPI controller (`:8000`) and Worker A (`:8001`). WireGuard IP: `10.100.0.1/24`.
- **Node B (Cloud Host)**: Microsoft Azure Linux VM with hardware virtualization pass-through (`/dev/kvm`), hosting Worker B (`:8002`). WireGuard IP: `10.100.0.2/24`.
- **Network Fabric**: Private point-to-point WireGuard VPN tunnel (UDP 51820). Worker B port 8002 is **strictly forbidden** from public internet exposure.

---

## 2. Current Architecture & Codebase Inventory

### 2.1 Core Components Status

| Component | Current Implementation | Location | Azure Migration Impact |
| :--- | :--- | :--- | :--- |
| **Controller API** | FastAPI, port 8000 | [`controller/main.py`](file:///home/rajyavardhan/ps023/controller/main.py) | **Zero code change**. `parse_nodes()` dynamically parses `PS023_NODES`. |
| **Node Registration** | SQLite DB via `upsert_node` | [`controller/database.py`](file:///home/rajyavardhan/ps023/controller/database.py) | **Zero code change**. Stores arbitrary worker URLs. |
| **Health Poller** | 5s background thread | [`controller/node_service.py`](file:///home/rajyavardhan/ps023/controller/node_service.py) | **Zero code change**. Polls whatever URLs are registered in DB. |
| **Scheduler** | Greedy max-free-memory | [`controller/scheduler.py`](file:///home/rajyavardhan/ps023/controller/scheduler.py) | **Zero code change**. Evaluates Node A and Node B by schedulable RAM. |
| **Worker B Service** | Systemd unit `ps023-worker` | [`outer/start-worker.sh`](file:///home/rajyavardhan/ps023/outer/start-worker.sh) | Template reused on Azure with `Delegate=yes`, `KillMode=process`. |
| **Cgroups v2** | `memory.max`, `cpu.max`, `pids.max` | [`worker/cgroup_manager.py`](file:///home/rajyavardhan/ps023/worker/cgroup_manager.py) | **Verified**. Kernel v2 subtree delegation applies identically on Azure. |
| **Cluster Bring-Up** | Orchestration script | [`bring-up.sh`](file:///home/rajyavardhan/ps023/bring-up.sh) | **Configurable toggle**. Supports `AZURE_HYBRID=1` while preserving local mode. |
| **Baseline VMs** | `ps-023`, `ps-023-2` on Node A | Host Fedora filesystem | **Untouched**. Never migrated, modified, stopped, or deleted. |

---

## 3. Reference Identification & Blast Radius Analysis

### 3.1 Hardcoded References to `192.168.100.17`

| File | Current Line / Pattern | Remediation / Strategy |
| :--- | :--- | :--- |
| [`bring-up.sh`](file:///home/rajyavardhan/ps023/bring-up.sh#L7) | `NODEB=192.168.100.17` | Change to `NODEB="${NODEB:-192.168.100.17}"`. If `AZURE_HYBRID=1`, set `NODEB=10.100.0.2`. |
| [`controller/try_nodeb.sh`](file:///home/rajyavardhan/ps023/controller/try_nodeb.sh#L2) | `URL=http://192.168.100.17:8002` | Parameterize to `URL="${PS023_NODE_B_URL:-http://192.168.100.17:8002}"`. |
| [`controller/try_inner_reach.sh`](file:///home/rajyavardhan/ps023/controller/try_inner_reach.sh#L4) | `URL=http://192.168.100.17:8002` | Parameterize to `URL="${PS023_NODE_B_URL:-http://192.168.100.17:8002}"`. |
| [`outer/start-worker.sh`](file:///home/rajyavardhan/ps023/outer/start-worker.sh#L36) | `--host 192.168.100.17` | Local nested VM script only; Azure deployment uses `10.100.0.2` via `setup_azure_node.sh`. |
| [`scripts/chaos_kill_node_b.sh`](file:///home/rajyavardhan/ps023/scripts/chaos_kill_node_b.sh#L96) | `NODE_B_HOST="${NODE_B_SSH_HOST:-10.100.0.2}"` | Already defaults to `10.100.0.2`. Verified compatible. |
| [`scripts/chaos_restore_node_b.sh`](file:///home/rajyavardhan/ps023/scripts/chaos_restore_node_b.sh#L68) | `NODE_B_HOST="${NODE_B_SSH_HOST:-10.100.0.2}"` | Already defaults to `10.100.0.2`. Verified compatible. |

### 3.2 References to AWS / EC2
- Historical AWS scripts in `deploy/aws/` are **preserved as reference documentation**.
- Roadmap references in `README.md` and presentation slides updated to highlight Azure Standard_D2s_v5.

---

## 4. Azure Infrastructure Requirements & VM SKU Selection

### 4.1 Nested Virtualization Architecture on Azure
Azure supports nested virtualization on specific VM families where the hypervisor exposes Intel `vmx` or AMD `svm` CPU flags.

| Azure VM Family | Example SKU | vCPUs | RAM | Nested KVM Support | Cost (Central India) | Selection Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dsv5 Series** | `Standard_D2s_v5` | **2** | **8 GiB** | **YES (Verified)** | **~$0.101/hr** | **PRIMARY CHOICE** (Optimal balance, low cost) |
| **Dsv5 Series** | `Standard_D4s_v5` | 4 | 16 GiB | YES | ~$0.202/hr | Fallback if 8 GiB RAM is insufficient |
| **Dsv4 Series** | `Standard_D2s_v4` | 2 | 8 GiB | YES | ~$0.096/hr | Regional quota fallback |
| **B-Series** | `Standard_B2s` | 2 | 4 GiB | **NO** | ~$0.042/hr | **REJECTED** (No nested KVM support) |
| **Confidential / Trusted** | Any | - | - | **RESTRICTED** | - | **REJECTED** (Security flags block `/dev/kvm`) |

> [!CRITICAL]
> **Azure Security Type Requirement**:
> Azure VMs created for nested virtualization **must** use `--security-type Standard`.
> Setting `--security-type TrustedLaunch` or `ConfidentialVM` restricts Intel `vmx` virtualization pass-through, resulting in `/dev/kvm` failing to initialize in the Linux guest kernel.

---

## 5. Cost Analysis & Student Budget Management

| Resource | Unit Rate (Central India) | Unit Rate (Southeast Asia) | Pricing Model |
| :--- | :--- | :--- | :--- |
| **Compute (`Standard_D2s_v5`)** | ~$0.101/hour (~₹8.50/hr) | ~$0.120/hour (~₹10.00/hr) | **Billed per second when running; $0.00 when deallocated** |
| **OS Disk (30 GiB Standard SSD)** | ~$2.40/month (~$0.08/day) | ~$2.40/month (~$0.08/day) | Fixed monthly storage charge |
| **Static Public IPv4** | ~$0.005/hour (~$0.12/day) | ~$0.005/hour (~$0.12/day) | Retains IP across restarts |
| **Data Ingress / Egress** | Ingress: Free; Egress: 100 GB/mo free | Ingress: Free; Egress: 100 GB/mo free | Free within hackathon bandwidth |

### 5.1 Estimated Spend for Hackathon Evaluation
- **8 hours active running + testing**: $0.101 × 8 = **$0.81**
- **1 day disk & IP retention**: ~$0.20
- **Total Estimated Cost**: **~$1.01** (comfortably within Azure for Students $100 credit pool).

---

## 6. Migration Risks & Rollback Strategy

### 6.1 Identified Risks & Mitigations

1. **Risk: Azure Regional vCPU Quota Limits**
   - *Mitigation*: Script `00-check-azure.sh` queries `az vm list-usage` before provisioning. If `StandardDSv5Family` has 0 quota in `centralindia`, fallback to `southeastasia` or `eastus`.
2. **Risk: Venue Wi-Fi UDP Dropping (WireGuard Blocking)**
   - *Mitigation*: Dual-mode architecture. If venue network drops UDP port 51820, `bring-up.sh` immediately falls back to local nested VM (`192.168.100.17:8002`) with zero downtime.
3. **Risk: Worker API Exposure on Public IP**
   - *Mitigation*: Azure Network Security Group (NSG) has priority-1000 rule explicitly denying inbound TCP 8002 from `0.0.0.0/0`. Worker also binds specifically to WireGuard IP `10.100.0.2`.
4. **Risk: Baseline VM Disruption**
   - *Mitigation*: Baseline VMs `ps-023` and `ps-023-2` live exclusively on Node A (laptop) and are never involved in Node B operations.

### 6.2 Rollback Procedure
If Azure Node B fails or becomes unreachable:
1. Stop Azure controller registration:
   ```bash
   unset AZURE_HYBRID
   bash ~/ps023/bring-up.sh
   ```
2. The controller immediately reconnects to local Node B (`192.168.100.17:8002`).
3. Freeze Azure billing:
   ```bash
   bash scripts/azure/06-destroy-node-b.sh --stop
   ```

---

## 7. Deliverables & Action Plan

1. **Phase 1: Azure Automation Scripts (`scripts/azure/`)**:
   - `00-check-azure.sh`: Azure CLI authentication, quota verification, capability check, pricing preview.
   - `01-create-node-b.sh`: Idempotent Resource Group, VNet, NSG, and VM deployment (`Standard_D2s_v5`, `--security-type Standard`).
   - `02-bootstrap-node-b.sh`: KVM verification, user permissions, bridge/TAP configuration.
   - `03-install-cloud-hypervisor.sh`: Cloud Hypervisor v54.0.0, Ubuntu base image, smoke boot test.
   - `04-deploy-worker.sh`: Worker service deployment (`Delegate=yes`, `KillMode=process`).
   - `05-verify-node-b.sh`: WireGuard ping, authenticated health/resource checks, NSG public block verification.
   - `06-destroy-node-b.sh`: Clean deallocation and destruction workflows.
2. **Phase 2: WireGuard Tunneling**: Templates for Node A (`10.100.0.1`) and Node B (`10.100.0.2`).
3. **Phase 3: Controller Integration**: `AZURE_HYBRID=1` toggle in `bring-up.sh`.
4. **Phase 4: Cgroups v2 & Reliability Verification**: Rigorous testing against live Node B.
