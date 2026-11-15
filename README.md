# VM Controller

**VM Controller** is a virtualization management platform designed for Cloud Hypervisor microVMs, cluster scheduling, and guest lifecycle control across host and nested nodes.

---

## 1. Product Identity & Design System

The application has been upgraded into a technical, intentional, and modern infrastructure dashboard.

### Brand
The application is branded universally as **VM Controller**.

### Color Palette
Built around an infrastructure palette with dual light and dark theme support:

* **Warm Ivory (`#F5F0E6`)**: Primary light background and prominent text on dark surfaces.
* **Deep Charcoal (`#202522`)**: Navigation sidebar, dark workspace background, and prominent surfaces.
* **Emerald Green (`#168A62`)**: Healthy nodes, running virtual machines, successful operations.
* **Vermilion (`#E6533C`)**: Destructive actions, operation failures, node offline warnings.
* **Muted Sage (`#A7B9A8`)**: Secondary surfaces, subtle status indicators, borders.
* **Warm Stone (`#B9B1A5`)**: Dividers, secondary text, allocation bars.
* **Soft Gold (`#D8AA55`)**: Resource consumption warnings and selected accents.

---

## 2. Technology Stack

* **Frontend**: React 19 + TypeScript + Vite.
* **Icons**: [Lucide React](https://lucide.dev/).
* **Styling**: Pure CSS Design System with custom properties (`var(--...)`), full responsive layouts, light/dark themes.
* **Terminal Emulator**: `@xterm/xterm` + `@xterm/addon-fit` connected via real authenticated WebSockets.
* **Backend**: Python 3.14 + FastAPI + Starlette + Pydantic.
* **Database**: SQLite with foreign keys, schema migrations, operational events logging, and OS image catalog.
* **VMM**: Cloud Hypervisor direct-kernel boot (`vmlinux.bin` + RAW root disk + CIDATA FAT seed).
* **Testing**: `pytest` comprehensive test suite covering database, scheduler, image catalog, event logging, and API endpoints.

---

## 3. Application Architecture & Views

### Sidebar Navigation
1. **Overview**: Cluster capacity summary, active/stopped counts, schedulable RAM, live node allocation progress bars, quick operations, and scheduler advisory.
2. **Virtual Machines**: Search by name/ID/IP, filter by node/status, column sorting, resource detail breakdown, start, escalating stop, delete with confirmation modal, and terminal launcher.
3. **Nodes**: Telemetry cards for `node-a` and `node-b` showing health status, heartbeat age, CPU core counts, actual CPU utilization %, schedulable vs reserved vs physical RAM, and detailed inspection modal.
4. **Images & Operating Systems**: Catalog of Linux distributions (Ubuntu Server LTS, Debian, Fedora Server, Rocky Linux, AlmaLinux, openSUSE, Arch Linux), verification status, file paths, RAW format validation, import modal, and delete protection for in-use images.
5. **Terminals**: Full-screen dedicated multi-terminal workspace with multi-tab sessions, split-pane layout (side-by-side), font size controls, dark/light terminal themes, reconnection controls, and honest diagnostic states.
6. **Placement Decisions**: Scheduler decision history, candidate evaluations, verdicts (`eligible`, `refused`, `skipped`), and explanation of the memory invariant.
7. **Activity & Events**: Structured event stream for VM lifecycle, node heartbeats, scheduler rejections, terminal connections, and image imports.
8. **Settings**: API token configuration, polling interval adjustment (3s, 5s, 10s, 30s, manual), theme switcher, and cluster environment specs.

---

## 4. Virtualization & Cloud Hypervisor Compatibility

Cloud Hypervisor in this environment boots guests via direct kernel execution:
* **Kernel**: Uncompressed `vmlinux.bin` (or `vmlinux-net.bin` for nested outer hosts).
* **Command Line**: `console=ttyS0 root=/dev/vda1 rw`.
* **Disks**:
  1. Root filesystem disk: Raw disk image (`image_type=Raw`), expanded to configured `disk_gb`.
  2. Cloud-init seed: CIDATA FAT filesystem (`seed.img`) containing `user-data`, `meta-data`, and `network-config`.
* **Network**: Per-VM TAP devices (`tapvm0` - `tapvm7`) attached to bridge `br-ps023`.

### Supported Images
* **Ubuntu 24.04 LTS (Noble Numbat)**: Verified and bootable out of the box (`lab/images/ubuntu-noble.raw`).
* **Debian 12, Fedora 40, Rocky 9, AlmaLinux 9, openSUSE 15.6, Arch Linux**: Listed in catalog with official cloud mirror URLs. Custom RAW images can be imported via the UI. Unsupported formats or missing images cannot be selected for immediate boot.

---

## 5. Dedicated Terminal Workspace

Clicking **Terminal** on any running VM opens `/dashboard/#terminals?vm_id={vm_id}` (or `/terminals` / `/vms/{vm_id}/terminal-page`):
* **Real Transport**: Connected via WebSocket `/vms/{vm_id}/terminal` directly into the guest instance over SSH (`asyncssh`) using the VM's assigned IP.
* **Security**:
  * Authenticated with the bearer API token in the initial JSON handshake frame.
  * Restricted to VMs that are in `RUNNING` state with valid IP addresses.
  * Isolated PTY process per session with automatic cleanup on client disconnect.
  * Max 5 concurrent sessions enforced by the controller.
* **Honest Diagnostics**: If a VM is stopped, network initializing, or guest SSH daemon is not yet ready, the terminal presents diagnostics and actionable steps (e.g. "Start VM Now") rather than simulated output.

---

## 6. How to Run & Verify

### A. Environment & Secrets
Ensure secrets are configured in `secrets.env`:
```bash
PS023_API_TOKEN="your-secure-controller-bearer-token"
PS023_TOKEN_NODE_A="token-for-node-a"
PS023_TOKEN_NODE_B="token-for-node-b"
PS023_VM_PASSWORD="guest-ssh-password"
```

### B. Bring Up Cluster Infrastructure

**Mode 1: Local Development (Default)**
Brings up Node A on host laptop and Node B inside local nested VM:
```bash
bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
```

**Mode 2: Microsoft Azure Hybrid Cloud (Target Architecture)**
Connects local Node A controller with an independent Azure Linux VM (`Standard_D2s_v5`) over WireGuard:
```bash
# 1. Complete Azure deployment and WireGuard tunnel: see deploy/azure/README.md
# 2. Launch cluster in Azure Hybrid mode:
AZURE_HYBRID=1 bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
```
*(AWS EC2 deployment scripts and documentation remain available in `deploy/aws/README.md` as a historical prepared option).*

### C. Build the Frontend SPA
```bash
cd ~/ps023/frontend
npm run build
```
The compiled SPA is emitted directly to `controller/dashboard/`.

### D. Run Automated Test Suite
```bash
.venv/bin/pytest tests/ controller/ worker/
```
*(Runs 182 automated unit, integration, and security tests).*

### E. Primary Demonstration vs. Azure Hybrid Reference
- **Primary Demonstration Environment**: **Local Nested Node B** (`192.168.100.17` nested Cloud Hypervisor VM behind `br-ps023` bridge with `10.77.0.0/24` subnet routing). Provides 100% reliable, zero-network-dependency hardware virtualization demo.
- **Azure Hybrid Node B Reference**: Azure results (`ps023-node-b`, Standard_D2s_v4 in Central India) represent recorded benchmark runs from 13–14 Nov 2026. Transport modes evaluated:
  - `ssh-tunnel`: Verified and recorded on 13–14 Nov.
  - `wireguard`: Verified exclusively over a dedicated mobile hotspot (UDP 51820). The venue hostel Wi-Fi firewall blocks UDP 51820, preventing live WireGuard execution on site.
- **Documentation References**:
  - [Architectural Scope & Known Limitations](file:///home/rajyavardhan/ps023/docs/limitations.md)
  - [Comprehensive Evidence & Verification Index](file:///home/rajyavardhan/ps023/docs/EVIDENCE_INDEX.md)
  - [Live Demonstration Runbook](file:///home/rajyavardhan/ps023/docs/demo-script.md)

### F. Access the Dashboard
Open your browser to:
```
http://127.0.0.1:8000/
```
Enter your bearer token in the connect prompt to manage your Cloud Hypervisor cluster.

---

## 5. Fault Tolerance & Cold HA Failover

> [!NOTE]
> **Live Migration vs. Cold Failover**: Cloud Hypervisor microVMs run direct-kernel boots without shared SAN/Ceph storage or live memory serialization. True "live migration" across physical nodes is out-of-scope for microVM architectures. The system instead implements deterministic **cold HA failover** and stale ghost fencing.

### How HA Works
1. **Health Detection**: The controller continuously polls cluster nodes (`/resources`). If heartbeats cease beyond `PS023_UNHEALTHY_THRESHOLD_S` (default: 15s), the node is marked `UNHEALTHY`.
2. **Selective Auto-Evacuation (Cold Respawn)**: Non-HA VMs remain in `UNKNOWN` status. Running VMs marked `ha=true` transition through `EVACUATING`.
3. **Atomic Placement & Reservation**: The scheduler selects a healthy node with capacity (`scheduler.place()`). Target node memory is atomically reserved under lock to prevent oversubscription.
4. **Respawn & Recovery**: The microVM is cold-respawned on the healthy target node using its stored specification. Recovery duration is measured and logged to `decisions`.
5. **Stale Copy Fencing**: When the recovered node reconnects, reconciliation automatically detects stale ghost instances on the revived node and terminates/cleans them up using the 4-tier escalation (`delete_vm`).

### Configurable Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `PS023_UNHEALTHY_THRESHOLD_S` | `15.0` | Heartbeat silence threshold (seconds) before node marked UNHEALTHY |
| `PS023_EVACUATION_CONCURRENCY` | `3` | Maximum concurrent VM evacuations across threads |
| `PS023_EVACUATION_MAX_RETRIES` | `3` | Maximum retry attempts if placement fails due to capacity |
| `PS023_EVACUATION_BACKOFF_S` | `5.0` | Backoff period (seconds) before retrying failed evacuation |

### Live Chaos Demo Steps
1. **Create an HA VM on Node B**:
   ```bash
   curl -X POST -H "Authorization: Bearer $PS023_API_TOKEN" \
     -H "Content-Type: application/json" \
     http://127.0.0.1:8000/vms \
     -d '{"name": "ha-web", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "ha": true}'
   ```
2. **Simulate Node B Worker Crash / Sever Network**:
   ```bash
   ./scripts/chaos_kill_node_b.sh worker
   # (Or network mode: ./scripts/chaos_kill_node_b.sh network)
   ```
   The script measures and outputs exact timestamps:
   - Node kill timestamp
   - Controller UNHEALTHY detection delay (<15s)
   - VM evacuation and boot on Node A
   - Total recovery time (<20s target)
3. **Restore Node B & Verify Fencing**:
   ```bash
   ./scripts/chaos_restore_node_b.sh worker
   ```
   Verifies that Node B re-joins as HEALTHY and stale ghost copies on Node B are fenced without double-counting.
