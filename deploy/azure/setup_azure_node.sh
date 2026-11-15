#!/usr/bin/env bash
# ==============================================================================
# PS-023: Node B Setup Script for Microsoft Azure
# Target: Ubuntu Server 24.04 LTS (x86_64) on Standard_D2s_v5 (or D4s_v5)
# Validates nested KVM hardware virtualization, installs Cloud Hypervisor,
# configures bridge/TAP networking, and provisions worker service.
# Safe and idempotent to re-run.
# ==============================================================================
set -euo pipefail

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6 || echo "/home/$TARGET_USER")
WORKER_DIR="/opt/ps023-worker"
CH_VERSION="v54.0.0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Resolve worker source directory: support src/worker (submit repo) and worker/ (live repo)
WORKER_SRC=""
for cand in "$REPO_ROOT/src/worker" "$REPO_ROOT/worker" "$SCRIPT_DIR/../../src/worker" "$SCRIPT_DIR/../../worker" "$TARGET_HOME/src/worker" "$TARGET_HOME/worker" "./src/worker" "./worker"; do
  if [ -d "$cand" ] && [ -f "$cand/main.py" ] && [ -f "$cand/cgroup_manager.py" ]; then
    WORKER_SRC="$(cd "$cand" && pwd)"
    break
  fi
done

if [ -z "$WORKER_SRC" ]; then
  echo "ERROR: Could not resolve valid worker source directory containing main.py and cgroup_manager.py!" >&2
  echo "Checked candidates:" >&2
  echo "  - $REPO_ROOT/src/worker" >&2
  echo "  - $REPO_ROOT/worker" >&2
  exit 1
fi

WORKER_MODE="${PS023_WORKER_MODE:-}"
WORKER_BIND="${PS023_WORKER_BIND:-}"
DRY_RUN="${DRY_RUN:-0}"

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      ;;
    --wireguard)
      WORKER_MODE="wireguard"
      ;;
    --ssh)
      WORKER_MODE="ssh"
      ;;
  esac
done

if [ -z "$WORKER_BIND" ]; then
  if [ "$WORKER_MODE" = "wireguard" ]; then
    WORKER_BIND="10.100.0.2"
  else
    WORKER_BIND="127.0.0.1"
  fi
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "=== [DRY RUN] setup_azure_node.sh ==="
  echo "REPO_ROOT: $REPO_ROOT"
  echo "SCRIPT_DIR: $SCRIPT_DIR"
  echo "Resolved source path: $WORKER_SRC"
  echo "Worker bind host: $WORKER_BIND"
  echo "Files that would be copied to Node B ($WORKER_DIR/):"
  ls -1 "$WORKER_SRC"
  exit 0
fi

echo "======================================================================"
echo " PS-023: Microsoft Azure Node B Deployment Setup"
echo " Target User: $TARGET_USER ($TARGET_HOME)"
echo " Worker Dir:  $WORKER_DIR"
echo "======================================================================"
echo

# ------------------------------------------------------------------------------
# 1. Architecture and Hardware Virtualization Verification
# ------------------------------------------------------------------------------
echo "=== [1/8] Verifying CPU Architecture and Nested KVM Support ==="

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
  echo "ERROR: Unsupported architecture '$ARCH'. PS-023 requires x86_64." >&2
  exit 1
fi
echo "Architecture: $ARCH (OK)"

# Check RAM
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_MB=$((TOTAL_MEM_KB / 1024))
echo "Total Memory: ${TOTAL_MEM_MB} MB"
if [ "$TOTAL_MEM_MB" -lt 3500 ]; then
  echo "ERROR: Insufficient RAM (${TOTAL_MEM_MB} MB). At least 4 GiB (Standard_D2s_v5 recommended: 8 GiB) is required." >&2
  exit 1
fi

# Check Nested Virtualization CPU Flags (Intel VMX or AMD SVM)
if ! grep -q -E 'vmx|svm' /proc/cpuinfo; then
  echo "ERROR: CPU does not expose virtualization extensions ('vmx' or 'svm')." >&2
  echo "Nested virtualization is disabled or unsupported by the current Azure VM size." >&2
  echo "Please verify you selected an Intel/AMD VM supporting nested virtualization (e.g. Standard_D2s_v5, Standard_D4s_v5) with Security Type = Standard." >&2
  exit 1
fi
echo "Virtualization CPU flags (vmx/svm) detected in /proc/cpuinfo."

# Check /dev/kvm
if [ ! -e /dev/kvm ]; then
  echo "WARNING: /dev/kvm device node not immediately found. Attempting to modprobe kvm_intel..."
  modprobe kvm || true
  modprobe kvm_intel || true
fi

if [ ! -e /dev/kvm ]; then
  echo "CRITICAL ERROR: /dev/kvm not available after loading KVM modules." >&2
  echo "Nested KVM virtualization is not enabled on this Azure VM instance." >&2
  echo "Troubleshooting steps:" >&2
  echo "  1. Verify the Azure VM size supports nested virtualization (Dsv5, Dv5, Dsv4, Dsv3)." >&2
  echo "  2. In Azure Portal, ensure VM 'Security type' was set to 'Standard' (not Confidential VM)." >&2
  echo "  3. Verify kernel dmesg: 'sudo dmesg | grep -i kvm'." >&2
  exit 1
fi

echo "/dev/kvm exists: $(ls -l /dev/kvm)"

# Add user to kvm group (never world-writable permissions on /dev/kvm)
echo "Adding user '$TARGET_USER' to 'kvm' group..."
sudo usermod -aG kvm "$TARGET_USER"

# ------------------------------------------------------------------------------
# 2. System Packages Installation
# ------------------------------------------------------------------------------
echo "=== [2/8] Installing Required System Packages ==="
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
  wireguard-tools \
  iptables \
  iproute2 \
  iputils-ping \
  mtools \
  dosfstools \
  bridge-utils \
  socat \
  jq

# ------------------------------------------------------------------------------
# 3. Cloud Hypervisor Installation & Verification
# ------------------------------------------------------------------------------
echo "=== [3/8] Installing Cloud Hypervisor ${CH_VERSION} ==="
CURRENT_CH_VER=""
if command -v cloud-hypervisor >/dev/null 2>&1; then
  CURRENT_CH_VER=$(cloud-hypervisor --version 2>&1 || true)
fi

if [ "$CURRENT_CH_VER" != "cloud-hypervisor ${CH_VERSION}" ]; then
  echo "Downloading Cloud Hypervisor ${CH_VERSION} binary..."
  sudo curl -fsSL -o /usr/local/bin/cloud-hypervisor \
    "https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/${CH_VERSION}/cloud-hypervisor"
  sudo chmod +x /usr/local/bin/cloud-hypervisor

  echo "Downloading ch-remote ${CH_VERSION} binary..."
  sudo curl -fsSL -o /usr/local/bin/ch-remote \
    "https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/${CH_VERSION}/ch-remote"
  sudo chmod +x /usr/local/bin/ch-remote
fi

# Verify execution
INSTALLED_VER=$(/usr/local/bin/cloud-hypervisor --version)
echo "Installed: $INSTALLED_VER"

# ------------------------------------------------------------------------------
# 4. IP Forwarding & Persistent Sysctl
# ------------------------------------------------------------------------------
echo "=== [4/8] Configuring IP Forwarding ==="
sudo tee /etc/sysctl.d/99-ps023-ipforward.conf > /dev/null << 'EOF'
net.ipv4.ip_forward=1
EOF
sudo sysctl -q -p /etc/sysctl.d/99-ps023-ipforward.conf

# ------------------------------------------------------------------------------
# 5. Network Initialization Script (Bridge & TAP Devices)
# ------------------------------------------------------------------------------
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

# Enable NAT MASQUERADE for 192.168.200.0/24 egress
iptables -t nat -C POSTROUTING -s 192.168.200.0/24 ! -d 192.168.200.0/24 -j MASQUERADE 2>/dev/null || \
iptables -t nat -A POSTROUTING -s 192.168.200.0/24 ! -d 192.168.200.0/24 -j MASQUERADE

# Bridge forwarding filter rules
iptables -C FORWARD -i br-ps023 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i br-ps023 -j ACCEPT
iptables -C FORWARD -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
EOF
sudo chmod +x /usr/local/lib/ps023/ps023-net-init.sh

# Run network initialization immediately
sudo /usr/local/lib/ps023/ps023-net-init.sh

# ------------------------------------------------------------------------------
# 6. Persistent Systemd Service for Network
# ------------------------------------------------------------------------------
echo "=== [6/8] Installing Persistent Network Systemd Unit ==="
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

# ------------------------------------------------------------------------------
# 7. Setting Up Worker Directory & Python Virtual Environment
# ------------------------------------------------------------------------------
echo "=== [7/8] Provisioning Worker Directory & Environment ==="
sudo mkdir -p "$WORKER_DIR" "$WORKER_DIR/vms" "$WORKER_DIR/images" "$WORKER_DIR/kernel" "$WORKER_DIR/worker"
sudo chown -R "$TARGET_USER:$TARGET_USER" "$WORKER_DIR"

cp -r "$WORKER_SRC/"* "$WORKER_DIR/"
cp -r "$WORKER_SRC/"* "$WORKER_DIR/worker/" 2>/dev/null || true

# Set up dedicated Python virtual environment for worker
if [ ! -d "$WORKER_DIR/venv" ]; then
  python3 -m venv "$WORKER_DIR/venv"
fi
"$WORKER_DIR/venv/bin/pip" install --upgrade pip -q
"$WORKER_DIR/venv/bin/pip" install -q fastapi uvicorn httpx pydantic psutil

# Prepare worker.env template if not already present
if [ ! -f "$WORKER_DIR/worker.env" ]; then
  cat > "$WORKER_DIR/worker.env" << EOF
PS023_NODE_ID=node-b
PS023_WORKER_BIND=$WORKER_BIND
PS023_WORKER_TOKEN=REPLACE_WITH_PS023_TOKEN_NODE_B
PS023_SUBNET=192.168.200
PS023_SLOT_START=0
PS023_SLOT_COUNT=8
PS023_VM_PASSWORD=REPLACE_WITH_VM_PASSWORD
PS023_VM_ROOT=/opt/ps023-worker/vms
PS023_BASE_IMAGE=/opt/ps023-worker/images/ubuntu-noble.raw
PS023_KERNEL=/opt/ps023-worker/kernel/vmlinux.bin
EOF
  chmod 600 "$WORKER_DIR/worker.env"
  echo "Created template: $WORKER_DIR/worker.env"
fi

# ------------------------------------------------------------------------------
# 8. Creating Systemd Service for Worker ($WORKER_BIND:8002)
# ------------------------------------------------------------------------------
echo "=== [8/8] Creating Systemd Service for Worker ($WORKER_BIND) ==="
if [ "$WORKER_BIND" = "10.100.0.2" ]; then
  WG_WANTS="Wants=wg-quick@wg0.service ps023-network.service"
else
  WG_WANTS="Wants=ps023-network.service"
fi

sudo tee /etc/systemd/system/ps023-worker.service > /dev/null << EOF
[Unit]
Description=PS-023 Cloud Hypervisor Worker Agent (Node B - Azure)
After=network.target ps023-network.service wg-quick@wg0.service
$WG_WANTS

[Service]
Type=simple
User=$TARGET_USER
Group=$TARGET_USER
WorkingDirectory=$WORKER_DIR
EnvironmentFile=$WORKER_DIR/worker.env
ExecStart=$WORKER_DIR/venv/bin/uvicorn main:app --host $WORKER_BIND --port 8002
Restart=always
RestartSec=3
LimitNOFILE=65536
Delegate=yes
DelegateSubgroup=service
KillMode=process

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

echo
echo "======================================================================"
echo "Azure Node B Base Provisioning Complete!"
echo "1. Nested KVM verified: /dev/kvm available."
echo "2. Bridge 'br-ps023' (192.168.200.1/24) & tapvm0..tapvm7 initialized."
echo "3. Cloud Hypervisor ${CH_VERSION} installed."
echo "4. Worker files placed in $WORKER_DIR."
echo "5. Next steps:"
echo "   a. Fill secrets in: $WORKER_DIR/worker.env"
echo "   b. Run: sudo bash deploy/azure/wg_setup_node_b.sh"
echo "   c. Start worker: sudo systemctl enable --now ps023-worker"
echo "======================================================================"
