# Microsoft Azure Node B Deployment Guide (PS-023)

This guide documents the complete, step-by-step instructions for launching and configuring **Node B** on **Microsoft Azure** as an independent Linux virtual machine running nested hardware virtualization (KVM) and joining it to the PS-023 Cloud Hypervisor cluster over an encrypted WireGuard VPN tunnel.

---

## 1. Architecture Overview

```
+------------------------------------+          WireGuard VPN Tunnel (UDP 51820)         +-------------------------------------+
|        Node A (Laptop Host)        | <===============================================> |         Node B (Azure VM)           |
|                                    |                                                   | Type: Standard_D2s_v5 (Nested KVM)  |
| • Controller: http://127.0.0.1:8000|                                                   | • WireGuard IP: 10.100.0.2/24       |
| • Worker A:   http://127.0.0.1:8001|                                                   | • Worker B:     http://10.100.0.2:8002|
| • WireGuard IP: 10.100.0.1/24      |                                                   | • Bridge:       br-ps023            |
| • Bridge:     br-ps023             |                                                   |                 (192.168.200.1/24)  |
|               (192.168.100.1/24)   |                                                   | • Guests:       tapvm0..tapvm7      |
| • Guests:     tapvm0..tapvm7       |                                                   | • Hypervisor:   Cloud Hypervisor    |
+------------------------------------+                                                   +-------------------------------------+
```

---

## 2. Recommended Azure VM Specifications

| Property | Recommendation | Fallback |
| :--- | :--- | :--- |
| **VM Size** | `Standard_D2s_v5` | `Standard_D4s_v5` (or `Standard_D2s_v4`) |
| **vCPUs** | 2 vCPUs | 4 vCPUs |
| **RAM** | 8 GiB | 16 GiB |
| **Architecture** | x86-64 | x86-64 |
| **Processor** | 3rd Gen Intel Xeon Platinum (Ice Lake) | 3rd/4th Gen Intel Xeon |
| **Nested KVM** | **Supported & Verified** (`vmx`) | Supported |
| **Target Regions** | `centralindia` (Pune, India) | `southeastasia` (Singapore) |
| **Security Type** | **Standard** (Required for Nested KVM) | Standard |
| **OS Image** | Ubuntu Server 24.04 LTS (x86_64 Gen 2) | Ubuntu 22.04 LTS |
| **OS Disk** | 30 GiB Standard SSD (StandardSSD_LRS) | 30 GiB Premium SSD |

> [!IMPORTANT]
> **Nested Virtualization Prerequisite in Azure**:
> When creating the VM in Azure, ensure the **Security type** is set to **Standard**.
> Modern Azure defaults to *Trusted Launch* or *Confidential VM* on some images, which can restrict hardware-level virtualization pass-through (`/dev/kvm`). Standard security ensures the Intel `vmx` virtualization flags are cleanly passed into the Linux kernel.

---

## 3. Cost Breakdown & Budget Estimates

| Resource | Hourly Rate (Central India) | Hourly Rate (Southeast Asia) | Monthly Base | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `Standard_D2s_v5` Compute | ~$0.101/hr (~₹8.50/hr) | ~$0.120/hr (~₹10.00/hr) | $0 when deallocated | Incurs charges only when running |
| 30 GiB Standard SSD | - | - | ~$2.40/month (~$0.08/day) | Persists when VM is deallocated |
| Static Public IPv4 | ~$0.005/hr (~$0.12/day) | ~$0.005/hr (~$0.12/day) | ~$3.60/month | Retains IP address across restarts |
| Inbound / Internal Traffic | Free | Free | Free | Included |

**Estimated cost for 1 day of intensive evaluation (8 hours running, 16 hours deallocated):**
- Compute: $0.101 × 8 = **$0.81**
- Storage + IP: ~$0.15
- **Total:** ~**$0.96** (well within student budget).

---

## 4. Azure for Students Eligibility & Quota Pre-Check

Before provisioning, verify your Azure for Students subscription quotas:
1. Log in to [Azure Portal](https://portal.azure.com).
2. Navigate to **Subscriptions** -> Select your Student Subscription -> **Usage + quotas**.
3. Filter by Location: `Central India` (or `Southeast Asia`).
4. Look for:
   - **Total Regional vCPUs**: Needs $\ge 2$.
   - **Standard DSv5 Family vCPUs**: Needs $\ge 2$.
5. If DSv5 is restricted or unavailable in Central India for your student tier, switch to `southeastasia` or test `Standard_D2s_v4`.

---

## 5. Step-by-Step Deployment Instructions

### Step 5.1: Provision the Azure VM

You can provision via the Azure Portal or using the Azure CLI.

#### Option A: Using the Interactive Planner Script (Recommended)
From your laptop:
```bash
# Preview planned commands and cost
bash deploy/azure/azure_vm_provision.sh --dry-run
```

#### Option B: Azure CLI Commands
```bash
# 1. Set environment variables
export AZ_RG="rg-ps023"
export AZ_LOC="centralindia"  # or southeastasia
export MY_IP="$(curl -s https://api.ipify.org)/32"

# 2. Create Resource Group
az group create --name $AZ_RG --location $AZ_LOC

# 3. Create VNet and Subnet
az network vnet create \
  --resource-group $AZ_RG \
  --name vnet-ps023 \
  --address-prefix 10.0.0.0/16 \
  --subnet-name snet-node-b \
  --subnet-prefix 10.0.1.0/24

# 4. Create Network Security Group (NSG) with strict firewall rules
az network nsg create --resource-group $AZ_RG --name nsg-ps023-node-b

# Allow SSH from caller IP only
az network nsg rule create \
  --resource-group $AZ_RG --nsg-name nsg-ps023-node-b \
  --name Allow-SSH-Trusted --priority 1000 --direction Inbound \
  --access Allow --protocol Tcp --source-address-prefixes "$MY_IP" \
  --destination-port-ranges 22

# Allow WireGuard VPN tunnel from caller IP only
az network nsg rule create \
  --resource-group $AZ_RG --nsg-name nsg-ps023-node-b \
  --name Allow-WireGuard-UDP --priority 1010 --direction Inbound \
  --access Allow --protocol Udp --source-address-prefixes "$MY_IP" \
  --destination-port-ranges 51820

# Explicitly Deny Public Access to Worker Port 8002
az network nsg rule create \
  --resource-group $AZ_RG --nsg-name nsg-ps023-node-b \
  --name Deny-Worker-Public --priority 1020 --direction Inbound \
  --access Deny --protocol Tcp --source-address-prefixes "Internet" \
  --destination-port-ranges 8002

# 5. Allocate Static Public IP and Network Interface
az network public-ip create \
  --resource-group $AZ_RG --name pip-ps023-node-b \
  --sku Standard --allocation-method Static

az network nic create \
  --resource-group $AZ_RG --name nic-ps023-node-b \
  --vnet-name vnet-ps023 --subnet snet-node-b \
  --network-security-group nsg-ps023-node-b \
  --public-ip-address pip-ps023-node-b

# 6. Deploy VM (CRITICAL: --security-type Standard)
az vm create \
  --resource-group $AZ_RG \
  --name ps023-node-b \
  --nics nic-ps023-node-b \
  --image "Canonical:ubuntu-24_04-lts:server:latest" \
  --size "Standard_D2s_v4" \
  --admin-username ubuntu \
  --ssh-key-values ~/.ssh/id_rsa.pub \
  --os-disk-size-gb 30 \
  --storage-sku StandardSSD_LRS \
  --security-type Standard

# 7. Note the Public IP
AZURE_IP=$(az network public-ip show --resource-group $AZ_RG --name pip-ps023-node-b --query ipAddress -o tsv)
echo "Node B Public IP: $AZURE_IP"
```

---

### Step 5.2: Verify Nested KVM on Node B

SSH into the Azure VM:
```bash
ssh ubuntu@<AZURE_PUBLIC_IP>
```

Verify KVM hardware acceleration:
```bash
ls -l /dev/kvm
grep -E 'vmx|svm' /proc/cpuinfo
```
- `/dev/kvm` must exist (`crw-rw---- 1 root kvm`).
- Virtualization flags `vmx` must be present.

---

### Step 5.3: Run Automated Node B Setup

1. From your laptop, copy the worker and deployment files to Node B:
   ```bash
   scp -r deploy/azure ubuntu@<AZURE_PUBLIC_IP>:~/deploy
   scp -r worker ubuntu@<AZURE_PUBLIC_IP>:~/worker
   ```
2. On the Azure VM (via SSH):
   ```bash
   cd ~/deploy
   sudo bash setup_azure_node.sh
   ```
   This will:
   - Validate CPU, RAM, and `/dev/kvm`.
   - Install required system packages (`python3`, `wireguard`, `iptables`, `mtools`).
   - Download and verify Cloud Hypervisor v54.0.0 and `ch-remote`.
   - Provision bridge `br-ps023` (`192.168.200.1/24`), `tapvm0..tapvm7`, and NAT masquerade.
   - Configure persistent systemd services (`ps023-network.service` and `ps023-worker.service`).

---

### Step 5.4: Setup Encrypted WireGuard Tunnel

#### 1. Setup Node B:
On the Azure VM:
```bash
cd ~/deploy
sudo bash wg_setup_node_b.sh
```
Note the printed **Node B Public Key**.

#### 2. Setup Node A (Laptop):
On your laptop:
```bash
sudo bash deploy/azure/wg_setup_node_a.sh
```
Edit `/etc/wireguard/wg0.conf` on your laptop:
- Set `PublicKey = <NODE_B_PUBLIC_KEY>`
- Set `Endpoint = <AZURE_PUBLIC_IP>:51820`
Bring up the interface:
```bash
sudo wg-quick up wg0
```
Note your **Node A Public Key** (`sudo cat /etc/wireguard/node_a_public.key`).

#### 3. Complete Peer on Node B:
On the Azure VM:
Edit `/etc/wireguard/wg0.conf`:
- Replace `PLACEHOLDER_LAPTOP_PUBLIC_KEY` with Node A's Public Key.
Restart WireGuard:
```bash
sudo systemctl restart wg-quick@wg0
```

#### 4. Configure Worker Secrets & Start Service on Node B:
On the Azure VM:
```bash
sudo nano /opt/ps023-worker/worker.env
```
- Set `PS023_WORKER_TOKEN` matching `PS023_TOKEN_NODE_B` in your laptop's `secrets.env`.
- Set `PS023_VM_PASSWORD` matching `PS023_VM_PASSWORD`.

Enable and start the worker agent:
```bash
sudo systemctl enable --now ps023-worker
```

---

### Step 5.5: Verify Link and Deployment

From your laptop:
```bash
export PS023_TOKEN_NODE_B="<your_node_b_token>"
bash deploy/azure/verify_azure_deployment.sh
```
All 5 checks must pass:
- Local WireGuard interface -> **PASS**
- ICMP Ping to `10.100.0.2` -> **PASS**
- WireGuard Handshake -> **PASS**
- Unauthenticated Worker Health (`/health`) -> **PASS**
- Authenticated Worker Resources (`/resources`) -> **PASS**

### Step 5.6: Measure Real Boot Time (Benchmarking)
On the Azure VM:
```bash
bash ~/deploy/boot_test.sh
```
Measures real microVM boot latency under nested KVM on Azure `Standard_D2s_v5`.

---

## 6. Controller Integration

To start the controller with Node A local and Node B on Azure:

```bash
# In your terminal on the laptop:
export PS023_NODES="node-a=http://127.0.0.1:8001,node-b=http://10.100.0.2:8002"
bash ~/ps023/with-secrets.sh uvicorn controller.main:app --host 127.0.0.1 --port 8000
```

Or run `bring-up.sh` in hybrid cloud mode:
```bash
AZURE_HYBRID=1 bash bring-up.sh
```

---

## 7. Cost-Control & Cleanup Instructions

When you are done testing:

### Pause VM (Stop Billing):
```bash
# Deallocates the VM so you are not charged for compute:
az vm deallocate --resource-group rg-ps023 --name ps023-node-b
```

### Resume VM:
```bash
# Restarts the VM (Static Public IP preserves configuration):
az vm start --resource-group rg-ps023 --name ps023-node-b
```

### Permanent Teardown:
```bash
# Permanently delete the resource group and all components:
bash deploy/azure/cleanup_azure.sh delete
# or: az group delete --name rg-ps023 --yes --no-wait
```
