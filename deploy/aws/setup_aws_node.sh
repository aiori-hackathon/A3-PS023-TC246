#!/usr/bin/env bash
# ==============================================================================
# PS-023: Node B Setup Script (AWS EC2 c8i.xlarge with Nested Virtualization)
# Idempotent and safe to re-run.
# ==============================================================================
set -euo pipefail

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
WORKER_DIR="/opt/ps023-worker"
CH_VERSION="v54.0.0"

echo "=== [1/8] Checking KVM & Nested Virtualization ==="
if [ ! -e /dev/kvm ]; then
  echo "ERROR: /dev/kvm not found." >&2
  echo "Nested virtualization is not enabled. Stop the instance and enable it with: aws ec2 modify-instance-cpu-options --instance-id <id> --nested-virtualization enabled (or relaunch with --cpu-options NestedVirtualization=enabled). Make sure the type is C8i, M8i or R8i." >&2
  exit 1
fi

echo "Virtualization diagnostics:"
lscpu | grep -i virtualization || echo "  (Virtualization flags not reported by lscpu)"
lsmod | grep kvm || echo "  (kvm module loaded as built-in or active)"
echo "/dev/kvm exists and is accessible."

# Add user to kvm group (never chmod 666 /dev/kvm)
echo "Adding user '$TARGET_USER' to kvm group..."
sudo usermod -aG kvm "$TARGET_USER"

echo "=== [2/8] Installing System Packages ==="
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
  git \
  python3 \
  python3-venv \
  python3-pip \
  python3-psutil \
  openssl \
  curl \
  wireguard \
  iptables \
  iproute2 \
  iputils-ping \
  mtools \
  dosfstools

echo "=== [3/8] Installing Cloud Hypervisor ${CH_VERSION} ==="
if ! command -v cloud-hypervisor >/dev/null 2>&1 || [ "$(cloud-hypervisor --version 2>&1)" != "cloud-hypervisor ${CH_VERSION}" ]; then
  echo "Downloading Cloud Hypervisor ${CH_VERSION}..."
  sudo curl -fsSL -o /usr/local/bin/cloud-hypervisor \
    "https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/${CH_VERSION}/cloud-hypervisor"
  sudo chmod +x /usr/local/bin/cloud-hypervisor

  echo "Downloading ch-remote ${CH_VERSION}..."
  sudo curl -fsSL -o /usr/local/bin/ch-remote \
    "https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/${CH_VERSION}/ch-remote"
  sudo chmod +x /usr/local/bin/ch-remote
fi
cloud-hypervisor --version

echo "=== [4/8] Configuring IP Forwarding & Persistent Sysctl ==="
sudo tee /etc/sysctl.d/99-ps023-ipforward.conf > /dev/null << 'EOF'
net.ipv4.ip_forward=1
EOF
sudo sysctl -q -p /etc/sysctl.d/99-ps023-ipforward.conf

echo "=== [5/8] Creating Network Initialization Script ==="
sudo mkdir -p /usr/local/lib/ps023
sudo tee /usr/local/lib/ps023/ps023-net-init.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Create Bridge br-ps023 if not exists
if ! ip link show br-ps023 >/dev/null 2>&1; then
  ip link add br-ps023 type bridge
  ip addr add 192.168.200.1/24 dev br-ps023
fi
ip link set br-ps023 up

# Attach TAP devices tapvm0..tapvm7
for n in 0 1 2 3 4 5 6 7; do
  tap="tapvm$n"
  if ! ip link show "$tap" >/dev/null 2>&1; then
    ip tuntap add dev "$tap" mode tap user root
  fi
  ip link set "$tap" master br-ps023
  ip link set "$tap" up
done

# Enable NAT MASQUERADE for 192.168.200.0/24
iptables -t nat -C POSTROUTING -s 192.168.200.0/24 ! -d 192.168.200.0/24 -j MASQUERADE 2>/dev/null || \
iptables -t nat -A POSTROUTING -s 192.168.200.0/24 ! -d 192.168.200.0/24 -j MASQUERADE

# Forwarding filter rules for the bridge
iptables -C FORWARD -i br-ps023 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i br-ps023 -j ACCEPT
iptables -C FORWARD -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || iptables -A FORWARD -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
EOF
sudo chmod +x /usr/local/lib/ps023/ps023-net-init.sh

# Run network setup now
sudo /usr/local/lib/ps023/ps023-net-init.sh

echo "=== [6/8] Creating Persistent Systemd Service for Network ==="
sudo tee /etc/systemd/system/ps023-network.service > /dev/null << 'EOF'
[Unit]
Description=PS-023 Node B Bridge, TAP and NAT Provisioner
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/ps023/ps023-net-init.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable ps023-network.service

echo "=== [7/8] Setting Up Worker Directory & Python Virtual Environment ==="
sudo mkdir -p "$WORKER_DIR" "$WORKER_DIR/vms" "$WORKER_DIR/images" "$WORKER_DIR/kernel"
sudo chown -R "$TARGET_USER:$TARGET_USER" "$WORKER_DIR"

# If local worker code is passed or located nearby, copy it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../../worker/main.py" ]; then
  cp -r "$SCRIPT_DIR/../../worker/"* "$WORKER_DIR/"
elif [ -f "$TARGET_HOME/worker/main.py" ]; then
  cp -r "$TARGET_HOME/worker/"* "$WORKER_DIR/"
elif [ -f "./worker/main.py" ]; then
  cp -r ./worker/* "$WORKER_DIR/"
fi

# Create clean venv for worker
if [ ! -d "$WORKER_DIR/venv" ]; then
  python3 -m venv "$WORKER_DIR/venv"
fi
"$WORKER_DIR/venv/bin/pip" install --upgrade pip -q
"$WORKER_DIR/venv/bin/pip" install -q fastapi uvicorn httpx pydantic psutil

# Prepare worker environment file if not already present
if [ ! -f "$WORKER_DIR/worker.env" ]; then
  cat > "$WORKER_DIR/worker.env" << 'EOF'
PS023_NODE_ID=node-b
PS023_WORKER_TOKEN=REPLACE_WITH_PS023_TOKEN_NODE_B
PS023_SUBNET=192.168.200
PS023_SLOT_START=0
PS023_SLOT_COUNT=8
PS023_VM_PASSWORD=REPLACE_WITH_VM_PASSWORD
PS023_VM_ROOT=/opt/ps023-worker/vms
PS023_BASE_IMAGE=/opt/ps023-worker/images/ubuntu-noble.raw
PS023_KERNEL=/opt/ps023-worker/kernel/vmlinux.bin
EOF
  echo "Created $WORKER_DIR/worker.env template."
fi

echo "=== [8/8] Creating Systemd Service for Worker (10.100.0.2:8002) ==="
sudo tee /etc/systemd/system/ps023-worker.service > /dev/null << EOF
[Unit]
Description=PS-023 Cloud Hypervisor Worker Agent (Node B)
After=network.target ps023-network.service wg-quick@wg0.service
Wants=wg-quick@wg0.service ps023-network.service

[Service]
Type=simple
User=$TARGET_USER
Group=$TARGET_USER
WorkingDirectory=$WORKER_DIR
EnvironmentFile=$WORKER_DIR/worker.env
ExecStart=$WORKER_DIR/venv/bin/uvicorn main:app --host 10.100.0.2 --port 8002
Restart=always
RestartSec=3
LimitNOFILE=65536
Delegate=yes
KillMode=process

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

echo
echo "======================================================================"
echo "Node B Base Provisioning Complete!"
echo "1. Bridge 'br-ps023' (192.168.200.1/24) & tapvm0..tapvm7 initialized."
echo "2. Cloud Hypervisor ${CH_VERSION} installed to /usr/local/bin."
echo "3. Worker files placed in $WORKER_DIR."
echo "4. Update $WORKER_DIR/worker.env with the node token & password."
echo "5. Run wg_setup_node_b.sh to establish the WireGuard tunnel."
echo "6. Start worker with: sudo systemctl enable --now ps023-worker"
echo "======================================================================"
