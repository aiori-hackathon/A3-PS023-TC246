# AWS EC2 Node B Deployment Guide (PS-023)

This guide documents the exact, step-by-step instructions for launching and configuring **Node B** as an AWS EC2 instance running nested hardware virtualization (KVM) and joining it to the hybrid Cloud Hypervisor cluster over an encrypted WireGuard tunnel.

---

## Architecture Overview

```
+------------------------------------+          WireGuard VPN Tunnel (UDP 51820)         +-------------------------------------+
|        Node A (Laptop Host)        | <===============================================> |         Node B (AWS EC2)            |
|                                    |                                                   | Type: c8i.xlarge (Nested KVM)       |
| • Controller: http://127.0.0.1:8000|                                                   | • WireGuard IP: 10.100.0.2/24       |
| • Worker A:   http://127.0.0.1:8001|                                                   | • Worker B:     http://10.100.0.2:8002|
| • WireGuard IP: 10.100.0.1/24      |                                                   | • Bridge:       br-ps023            |
| • Bridge:     br-ps023             |                                                   |                 (192.168.200.1/24)  |
|               (192.168.100.1/24)   |                                                   | • Guests:       tapvm0..tapvm7      |
+------------------------------------+                                                   +-------------------------------------+
```

---

## Step 1: Launch EC2 Instance with Nested Virtualization

In the **AWS Management Console** (EC2 Dashboard):

1. Click **Launch Instance**.
2. **Name**: `ps023-node-b`
3. **Application and OS Images (AMI)**:
   - Select **Ubuntu**.
   - Choose **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type** (64-bit x86).
4. **Instance Type**:
   - Select **`c8i.xlarge`** (4 vCPUs, 16 GiB RAM).
   - *Note*: `c8i`, `m8i`, or `r8i` instances are required because they run on Intel Xeon 6 (Granite Rapids) processors that support hardware-assisted nested virtualization on AWS EC2 without bare metal pricing.
5. **Key Pair**:
   - Select an existing key pair or create a new one (e.g. `ps023-key.pem`).
   - Store the `.pem` file safely on your laptop (e.g. `~/.ssh/ps023-key.pem`) and run `chmod 400 ~/.ssh/ps023-key.pem`.
   - **Never commit `.pem` files to the repository!**
6. **Storage**:
   - Set Root Volume size to at least **30 GiB** (gp3) to store Cloud Hypervisor guest VM raw images.
7. **Advanced Details -> CPU Options (CRITICAL)**:
   - Expand **Advanced Details** at the bottom of the launch page.
   - Scroll to **CPU options**.
   - Check/enable **Nested virtualization** (`NestedVirtualization=enabled`).
   - *Alternatively via AWS CLI*:
     ```bash
     aws ec2 run-instances \
       --image-id <ubuntu-24.04-ami-id> \
       --instance-type c8i.xlarge \
       --key-name ps023-key \
       --cpu-options NestedVirtualization=enabled \
       --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]'
     ```
8. Click **Launch Instance**.

---

## Step 2: Configure Security Group (Strict Firewall Rules)

Create or attach a dedicated Security Group: `ps023-node-b-sg`.

### Inbound Rules (Minimal Attack Surface)
| Type | Protocol | Port Range | Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | `My IP` (`<your-public-ip>/32`) | Direct secure administration |
| **Custom UDP** | UDP | `51820` | `My IP` (`<your-public-ip>/32`) | WireGuard VPN tunnel endpoint |

> [!CAUTION]
> **NEVER open TCP port 8002 to the public internet (`0.0.0.0/0`)!**
> The Worker agent HTTP API must only listen on and be reached through the encrypted WireGuard tunnel (`http://10.100.0.2:8002`).

### Outbound Rules
| Type | Protocol | Port Range | Destination | Description |
| :--- | :--- | :--- | :--- | :--- |
| **All traffic** | All | All | `0.0.0.0/0` | Package updates & OS images |

---

## Step 3: Allocate & Attach Elastic IP

1. In the EC2 Console, go to **Network & Security -> Elastic IPs**.
2. Click **Allocate Elastic IP address** and click **Allocate**.
3. Select the allocated Elastic IP -> **Actions -> Associate Elastic IP address**.
4. Choose the `ps023-node-b` instance and click **Associate**.
5. Note this IP: `<AWS_ELASTIC_IP>`.

---

## Step 4: Verify Hardware Virtualization (/dev/kvm)

Connect to the instance via SSH:
```bash
ssh -i ~/.ssh/ps023-key.pem ubuntu@<AWS_ELASTIC_IP>
```

Verify KVM hardware acceleration:
```bash
ls -l /dev/kvm
lscpu | grep -i virtualization
```
- Expected output: `/dev/kvm` must exist (`crw-rw---- 1 root kvm`).
- If missing, stop the instance in AWS Console, run:
  ```bash
  aws ec2 modify-instance-cpu-options --instance-id <instance-id> --nested-virtualization enabled
  ```
  and start the instance again.

---

## Step 5: Run Automated Provisioning on Node B

1. From your laptop, copy the deployment scripts and worker code to Node B:
   ```bash
   scp -i ~/.ssh/ps023-key.pem -r deploy/aws ubuntu@<AWS_ELASTIC_IP>:~/deploy
   scp -i ~/.ssh/ps023-key.pem -r worker ubuntu@<AWS_ELASTIC_IP>:~/worker
   ```
2. On Node B (via SSH):
   ```bash
   cd ~/deploy
   sudo bash setup_aws_node.sh
   ```
   This will:
   - Install required packages (git, python3, python3-psutil, wireguard, iptables, mtools).
   - Add user `ubuntu` to `kvm` group.
   - Install Cloud Hypervisor v54.0.0 and ch-remote to `/usr/local/bin`.
   - Provision bridge `br-ps023` (`192.168.200.1/24`), `tapvm0..tapvm7`, and NAT masquerade.
   - Install persistent systemd units (`ps023-network.service` and `ps023-worker.service`).

---

## Step 6: Setup WireGuard VPN Tunnel

### 1. Setup Node B:
On Node B (AWS EC2):
```bash
cd ~/deploy
sudo bash wg_setup_node_b.sh
```
Note the printed **Node B Public Key**.

### 2. Setup Node A (Laptop):
On your laptop:
```bash
sudo bash deploy/aws/wg_setup_node_a.sh
```
Edit `/etc/wireguard/wg0.conf` on your laptop:
- Set `PublicKey = <NODE_B_PUBLIC_KEY>`
- Set `Endpoint = <AWS_ELASTIC_IP>:51820`
Bring up the interface on your laptop:
```bash
sudo wg-quick up wg0
```
Note your **Node A Public Key** (from `sudo cat /etc/wireguard/node_a_public.key`).

### 3. Complete Peer on Node B:
On Node B (AWS EC2):
Edit `/etc/wireguard/wg0.conf`:
- Replace `PLACEHOLDER_LAPTOP_PUBLIC_KEY` with Node A's Public Key.
Restart WireGuard:
```bash
sudo systemctl restart wg-quick@wg0
```

### 4. Start Worker Service on Node B:
Configure secrets in `/opt/ps023-worker/worker.env`:
```bash
sudo nano /opt/ps023-worker/worker.env
# Set PS023_WORKER_TOKEN matching your PS023_TOKEN_NODE_B in secrets.env
# Set PS023_VM_PASSWORD matching your PS023_VM_PASSWORD
```
Start the worker:
```bash
sudo systemctl enable --now ps023-worker
```

### Updating an Already-Provisioned Node B Instance

If Node B was previously provisioned with the baseline unit, update the systemd unit to enable cgroup v2 subtree delegation and ensure VMM processes persist across worker restarts:

1. **Delete all VMs on Node B (or reboot Node B)**:
   > [!IMPORTANT]
   > Any existing VMs left running in the old service cgroup will occupy internal processes in the parent control group. Under cgroup v2's "no internal processes" rule, this completely prevents systemd and the worker from delegating controllers to child subtrees. Delete all active VMs on Node B (via controller API or `sudo pkill -9 -f cloud-hypervisor`) or reboot the instance before reconfiguring delegation.

2. **Connect to Node B via SSH**:
   ```bash
   ssh -i ~/.ssh/ps023-key.pem ubuntu@<AWS_ELASTIC_IP>
   ```

3. **Edit `/etc/systemd/system/ps023-worker.service`**:
   ```bash
   sudo nano /etc/systemd/system/ps023-worker.service
   ```
   Under the `[Service]` section, verify or append:
   ```ini
   Delegate=yes
   KillMode=process
   ```
   * `Delegate=yes`: Grants the unprivileged worker process permission to manage and delegate cgroup v2 controllers (`cpu`, `memory`, `pids`) to child cgroups (`ps023-vmm-<vm_id>`).
   * `KillMode=process`: Instructs systemd on service restart/stop to only terminate the main uvicorn process, leaving running Cloud Hypervisor VMM child processes intact.

4. **Reload systemd and restart the worker agent**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ps023-worker
   ```

> [!WARNING]
> **Live Verification Required**:
> While `KillMode=process` and `start_new_session=True` are configured to prevent systemd from killing the process tree, this restart survival behavior must be tested live on an active EC2 instance running Cloud Hypervisor. Do not claim VMM survival across service restart on Node B is verified until tested live on the instance.

---

## Step 7: Verify Tunnel and Measure Boot Time

### Verify Tunnel Link (from laptop):
```bash
bash deploy/aws/verify_link.sh
```
Expected:
- Check 1: ICMP Ping (10.100.0.2) -> **PASS**
- Check 2: WireGuard Handshake -> **PASS**
- Check 3: HTTP Health Probe (`http://10.100.0.2:8002/health`) -> **PASS**

### Measure Real Boot Time (on Node B):
On Node B (AWS EC2):
```bash
bash ~/deploy/boot_test.sh
```
This boots a microVM on AWS under nested KVM and records real boot latency in milliseconds and seconds to confirm performance for hackathon judging.

---

## Step 8: Cost Management Reminder

> [!IMPORTANT]
> **STOP the instance when not actively in use!**
> `c8i.xlarge` runs on high-performance compute hardware and incurs on-demand charges while in `running` state.
> - To stop: AWS Console -> EC2 -> Select `ps023-node-b` -> **Instance state -> Stop instance**.
> - Stopped instances only incur minimal EBS root storage fees (30 GB gp3 ≈ $2.40/month).
> - When ready to test again, **Start instance** (the Elastic IP ensures the IP address stays the same).
