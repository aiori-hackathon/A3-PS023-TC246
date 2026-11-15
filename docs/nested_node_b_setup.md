# PS-023: Nested Node B Setup, Configuration & Reproduction Guide

This document records the persistence architecture of the Nested Node B virtual machine and details every manual configuration change applied to its disk image, along with exact commands to reproduce the setup from a pristine base image.

---

## 1. Disk Persistence Architecture

- **Primary Image Path**: `/home/rajyavardhan/ps023/outer/disk.raw`
- **Virtual Size**: 20 GiB (Sparse physical allocation: ~6.7 GiB).
- **Persistence Across Bring-Up Runs**: **Persistent**.
  - As defined in [start-outer.sh](file:///home/rajyavardhan/ps023/outer/start-outer.sh), Cloud Hypervisor directly attaches `--disk path=$D/disk.raw,image_type=raw`.
  - The script does **not** re-clone or re-seed `disk.raw` during `bring-up.sh`. Any system package installations, systemd unit definitions, and python files written to the inner filesystem persist across reboots and bring-up invocations.
- **Backup Image**:
  - **Path**: `/home/rajyavardhan/ps023_backups/nested_node_b_disk_20261115.raw`
  - **Size**: 20 GiB virtual (6.7 GiB allocated on disk via sparse copy).
  - **Permissions**: `0600` (`-rw-------.`, owned by user `rajyavardhan`, outside git).

---

## 2. Inventory of Changes Applied Inside Nested Node B

### A. Systemd Unit Configuration (`/etc/systemd/system/ps023-worker.service`)
To ensure compliance with cgroup v2's "no internal processes" constraint during worker restarts when microVMs are preserved (`worker-preserve-vms` mode), the unit defines a dedicated delegated service subgroup:
```ini
[Unit]
Description=PS-023 Cloud Hypervisor Worker Agent (Node B)
After=network.target

[Service]
Type=simple
User=rajyavardhan
Group=rajyavardhan
WorkingDirectory=/home/rajyavardhan/worker
EnvironmentFile=/home/rajyavardhan/worker.env
ExecStart=/home/rajyavardhan/venv/bin/uvicorn main:app --host 192.168.100.17 --port 8002
Restart=always
RestartSec=3
LimitNOFILE=65536
Delegate=yes
DelegateSubgroup=service
KillMode=process

[Install]
WantedBy=multi-user.target
```
- **`Delegate=yes`**: Delegates cgroups v2 controller management to the unit.
- **`DelegateSubgroup=service`**: Places the worker's own process into `/system.slice/ps023-worker.service/service`, leaving the parent unit cgroup available for sibling child slices (`ps023-vmm-<vm_id>`).
- **`KillMode=process`**: Prevents systemd from killing running Cloud Hypervisor child VMs when restarting only the worker daemon.

### B. Worker Cgroup Manager (`/home/rajyavardhan/worker/cgroup_manager.py`)
Nested Node B's worker cgroup manager was updated to detect the parent service unit cgroup:
```python
# If running inside a systemd delegated subgroup (e.g. DelegateSubgroup=service),
# use parent unit cgroup so the service subgroup remains a leaf for clean systemd restarts.
parent_cg = own_cg.parent
if parent_cg and parent_cg != own_cg and parent_cg.name.endswith(".service"):
    if self._try_setup_cgroup_dir(parent_cg, move_worker=False):
        self.base_dir = parent_cg
        self.enabled = True
        self.cleanup_empty_leftovers(min_age_seconds=0.0)
        return
```

### C. Worker Environment File (`/home/rajyavardhan/worker.env`)
```bash
PS023_WORKER_BIND=192.168.100.17
PS023_WORKER_PORT=8002
PS023_NODE_ID=node-b
PS023_SLOT_START=0
PS023_SLOT_COUNT=4
HOST_RESERVE_MB=1024
PS023_WORKER_TOKEN=<token_from_secrets>
```

---

## 3. Reproduction Commands from a Fresh Base Image

If recreating Nested Node B from a fresh Ubuntu 24.04 / Debian raw cloud image:

1. **Boot Base Image in Outer Cloud Hypervisor**:
   ```bash
   # On host: launch outer VM
   bash ~/ps023/outer/start-outer.sh
   ```

2. **Setup Inner Bridge & TAP Pool**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   SSHPASS="$PS023_VM_PASSWORD" sshpass -e ssh -o StrictHostKeyChecking=no rajyavardhan@192.168.100.17 "bash -s" < ~/ps023/outer/inner-net.sh
   '
   ```

3. **Deploy Worker Code & Dependencies**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   SSHPASS="$PS023_VM_PASSWORD" sshpass -e scp -r -o StrictHostKeyChecking=no ~/ps023/worker rajyavardhan@192.168.100.17:~/worker
   '
   ```

4. **Install & Configure Systemd Service**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   SSHPASS="$PS023_VM_PASSWORD" sshpass -e ssh -o StrictHostKeyChecking=no rajyavardhan@192.168.100.17 "
     cat << \"EOF\" | echo \$SSHPASS | sudo -S tee /etc/systemd/system/ps023-worker.service
   [Unit]
   Description=PS-023 Cloud Hypervisor Worker Agent (Node B)
   After=network.target

   [Service]
   Type=simple
   User=rajyavardhan
   Group=rajyavardhan
   WorkingDirectory=/home/rajyavardhan/worker
   EnvironmentFile=/home/rajyavardhan/worker.env
   ExecStart=/home/rajyavardhan/venv/bin/uvicorn main:app --host 192.168.100.17 --port 8002
   Restart=always
   RestartSec=3
   LimitNOFILE=65536
   Delegate=yes
   DelegateSubgroup=service
   KillMode=process

   [Install]
   WantedBy=multi-user.target
   EOF
     echo \$SSHPASS | sudo -S systemctl daemon-reload
     echo \$SSHPASS | sudo -S systemctl enable ps023-worker
   "
   '
   ```

5. **Deploy `worker.env` & Restart Service**:
   ```bash
   bash ~/ps023/with-secrets.sh bash -c '
   SSHPASS="$PS023_VM_PASSWORD" sshpass -e ssh -o StrictHostKeyChecking=no rajyavardhan@192.168.100.17 "
     echo \"PS023_WORKER_BIND=192.168.100.17\" > ~/worker.env
     echo \"PS023_WORKER_PORT=8002\" >> ~/worker.env
     echo \"PS023_NODE_ID=node-b\" >> ~/worker.env
     echo \"PS023_SLOT_START=0\" >> ~/worker.env
     echo \"PS023_SLOT_COUNT=4\" >> ~/worker.env
     echo \"HOST_RESERVE_MB=1024\" >> ~/worker.env
     echo \"PS023_WORKER_TOKEN=\$PS023_TOKEN_NODE_B\" >> ~/worker.env
     echo \$SSHPASS | sudo -S systemctl restart ps023-worker
   "
   '
   ```
