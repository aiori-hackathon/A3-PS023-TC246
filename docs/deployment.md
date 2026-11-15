# PS-023: Deployment Runbook & Environment Guide

## 1. Deployment Environments

### A. Primary Demo Environment: Local Fallback Cluster
- **Controller & Node A**: Host machine (Fedora Linux, kernel 6.x, direct KVM).
- **Node B**: Nested KVM guest (`192.168.100.17`) launched via `cloud-hypervisor` with nested virtualization enabled (`--cpus boot=4,kvm_hyperv=off`).
- **Network Topology**:
  - Host bridge: `br-ps023` (`192.168.100.1/24`).
  - Node A MicroVMs: `192.168.100.10+`.
  - Node B inner subnet: `10.77.0.0/24` routed via `ip route add 10.77.0.0/24 via 192.168.100.17 dev br-ps023`.

### B. Azure Hybrid Cloud Deployment (Historical Runs: 13–14 Nov 2026)
- **Node B VM**: `ps023-node-b` (Azure `Standard_D2s_v4`, Central India).
- **Transport Configurations**:
  - `ssh-tunnel`: Local port forward `8002 -> 127.0.0.1:8002` over SSH (`ssh -L 8002:127.0.0.1:8002`).
  - `wireguard`: Point-to-point WireGuard tunnel (`wg0`, `10.100.0.1` host <-> `10.100.0.2` Azure VM). Verified over mobile hotspot; venue Wi-Fi blocks UDP 51820.

---

## 2. Bring-Up Procedure (Local Fallback)

1. **Verify Host Prerequisites**:
   - Primed sudo credentials (`sudo -v`).
   - Cloud Hypervisor binary present at `/usr/local/bin/cloud-hypervisor`.
   - Kernel images at `/var/lib/ps023/images/vmlinux.bin`.

2. **Execute Automated Bring-Up**:
   ```bash
   bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
   ```
   **Expected Output**:
   - `=== 1. host network`: bridge `br-ps023` and 8 TAP devices ready.
   - `=== 2. node-b setup`: nested VM booted and responsive.
   - `=== 3. node-b inner network and worker`: worker B OK.
   - `=== 4. route to inner network`: `10.77.0.0/24 via 192.168.100.17`.
   - `=== 5. worker A and controller on host`: worker A OK, controller OK.
   - `=== 6. cluster state`: both nodes `HEALTHY`. `READY.`

3. **Verify Dashboard Access**:
   - Open browser at `http://127.0.0.1:8000/dashboard/`.
   - Connect using `PS023_API_TOKEN`.
