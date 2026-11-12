#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 2: Bootstrap Node B OS & KVM Networking
# Connects to Azure Node B over SSH to configure:
# - Nested KVM hardware virtualization verification
# - Virtual Bridge br-ps023 (192.168.200.1/24) and TAP pool (tapvm0..7)
# - System packages, user permissions, and WireGuard prerequisites
# Safe and idempotent to re-run.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

if [ -f "$SCRIPT_DIR/node_b.env" ]; then
  source "$SCRIPT_DIR/node_b.env"
fi

NODE_B_HOST="${1:-${AZURE_NODE_B_PUBLIC_IP:-}}"
if [ -z "$NODE_B_HOST" ]; then
  log_err "Missing Node B host IP. Pass it as \$1 or define in scripts/azure/node_b.env."
  echo "Usage: $0 <NODE_B_PUBLIC_IP>"
  exit 1
fi

SSH_USER="${AZURE_ADMIN_USER:-ubuntu}"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

log_info "Connecting to Azure Node B at $NODE_B_HOST ($SSH_USER)..."

ssh $SSH_OPTS "$SSH_USER@$NODE_B_HOST" 'bash -s' << 'REMOTE_BOOTSTRAP_EOF'
set -euo pipefail

echo "=== [1/5] Verifying CPU Virtualization Flags & /dev/kvm ==="
if ! grep -q -E 'vmx|svm' /proc/cpuinfo; then
  echo "CRITICAL: 'vmx' or 'svm' flag missing in /proc/cpuinfo!" >&2
  echo "Nested virtualization is not active. Ensure VM security type is Standard." >&2
  exit 1
fi
echo "✓ Hardware virtualization CPU flags detected."

if [ ! -e /dev/kvm ]; then
  sudo modprobe kvm || true
  sudo modprobe kvm_intel || true
fi

if [ ! -e /dev/kvm ]; then
  echo "CRITICAL: /dev/kvm does not exist after modprobe!" >&2
  exit 1
fi
echo "✓ /dev/kvm verified: $(ls -l /dev/kvm)"

sudo usermod -aG kvm "$USER"
echo "✓ User '$USER' added to 'kvm' group."

echo "=== [2/5] Installing Required System Packages ==="
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
  git python3 python3-venv python3-pip python3-psutil \
  openssl curl wireguard wireguard-tools iptables iproute2 \
  iputils-ping mtools dosfstools bridge-utils socat jq

echo "=== [3/5] Configuring Bridge br-ps023 & TAP Pool (tapvm0..7) ==="
if ! ip link show br-ps023 >/dev/null 2>&1; then
  sudo ip link add br-ps023 type bridge
  sudo ip addr add 192.168.200.1/24 dev br-ps023
  sudo ip link set br-ps023 up
  echo "✓ Bridge br-ps023 created with IP 192.168.200.1/24"
else
  echo "✓ Bridge br-ps023 already exists"
fi

for i in $(seq 0 7); do
  TAP="tapvm$i"
  if ! ip link show "$TAP" >/dev/null 2>&1; then
    sudo ip tuntap add dev "$TAP" mode tap user "$USER"
    sudo ip link set "$TAP" master br-ps023
    sudo ip link set "$TAP" up
  fi
done
echo "✓ Pre-allocated 8 TAP interfaces (tapvm0 to tapvm7) attached to br-ps023"

echo "=== [4/5] Enabling IPv4 Forwarding & NAT Masquerade ==="
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null
sudo iptables -t nat -C POSTROUTING -s 192.168.200.0/24 -j MASQUERADE 2>/dev/null || \
  sudo iptables -t nat -A POSTROUTING -s 192.168.200.0/24 -j MASQUERADE
echo "✓ Kernel IP forwarding and NAT masquerade active for 192.168.200.0/24"

echo "=== [5/5] Generating Node B WireGuard Keypair ==="
sudo mkdir -p /etc/wireguard
sudo chmod 700 /etc/wireguard
if [ ! -f /etc/wireguard/private.key ]; then
  sudo sh -c 'umask 077 && wg genkey | tee /etc/wireguard/private.key | wg pubkey > /etc/wireguard/public.key'
  echo "✓ New WireGuard keypair generated."
else
  echo "✓ WireGuard keypair already exists."
fi
PUB_KEY=$(sudo cat /etc/wireguard/public.key)
echo "Node B WireGuard Public Key: $PUB_KEY"
REMOTE_BOOTSTRAP_EOF

log_ok "Node B OS, KVM, Networking, and TAP devices successfully configured!"
echo "Proceed to 03-install-cloud-hypervisor.sh."
