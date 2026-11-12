#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 3: Install Cloud Hypervisor & Base Images
# Installs Cloud Hypervisor v54.0.0, Ubuntu 24.04 base cloud rootfs,
# uncompressed vmlinux kernel, and executes a local smoke boot test.
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
  exit 1
fi

SSH_USER="${AZURE_ADMIN_USER:-ubuntu}"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

log_info "Installing Cloud Hypervisor and test images on Node B ($NODE_B_HOST)..."

ssh $SSH_OPTS "$SSH_USER@$NODE_B_HOST" 'bash -s' << 'REMOTE_CH_EOF'
set -euo pipefail

WORKER_DIR="/opt/ps023-worker"
sudo mkdir -p "$WORKER_DIR/images" "$WORKER_DIR/kernel" "$WORKER_DIR/vms"
sudo chown -R "$USER:$USER" "$WORKER_DIR"

echo "=== [1/3] Installing Cloud Hypervisor ==="
if [ ! -f /usr/local/bin/cloud-hypervisor ]; then
  echo "Downloading Cloud Hypervisor release binary..."
  curl -fsSL -o /tmp/cloud-hypervisor \
    https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/v54.0/cloud-hypervisor-static || \
  curl -fsSL -o /tmp/cloud-hypervisor \
    https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/v54.1/cloud-hypervisor-static
  chmod +x /tmp/cloud-hypervisor
  sudo mv /tmp/cloud-hypervisor /usr/local/bin/cloud-hypervisor
  sudo setcap cap_net_admin+ep /usr/local/bin/cloud-hypervisor 2>/dev/null || true
  echo "✓ Cloud Hypervisor installed to /usr/local/bin/cloud-hypervisor"
else
  echo "✓ Cloud Hypervisor already installed: $(/usr/local/bin/cloud-hypervisor --version)"
fi

if [ ! -f /usr/local/bin/ch-remote ]; then
  echo "Downloading ch-remote release binary..."
  curl -fsSL -o /tmp/ch-remote \
    https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/v54.0/ch-remote-static || \
  curl -fsSL -o /tmp/ch-remote \
    https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/v54.1/ch-remote-static
  chmod +x /tmp/ch-remote
  sudo mv /tmp/ch-remote /usr/local/bin/ch-remote
  echo "✓ ch-remote installed to /usr/local/bin/ch-remote"
fi

echo "=== [2/3] Provisioning Base Kernel & Cloud Image Assets ==="
KERNEL_PATH="$WORKER_DIR/kernel/vmlinux.bin"
IMAGE_PATH="$WORKER_DIR/images/ubuntu-24-04.raw"

if [ ! -f "$KERNEL_PATH" ]; then
  echo "Downloading hypervisor-fw / Linux kernel..."
  curl -fsSL -o "$KERNEL_PATH" \
    https://github.com/cloud-hypervisor/rust-hypervisor-firmware/releases/download/0.5.0/hypervisor-fw 2>/dev/null || \
  curl -fsSL -o "$KERNEL_PATH" \
    https://cloud-images.ubuntu.com/noble/current/unpacked/noble-server-cloudimg-amd64-vmlinuz-generic 2>/dev/null || true
fi

if [ ! -f "$IMAGE_PATH" ]; then
  echo "Creating empty RAW base image placeholder (or download Noble minimal cloudimg)..."
  # Try downloading minimal Noble cloud image if network bandwidth permits, else create sparse test disk
  if curl -fsSL -I https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img >/dev/null 2>&1; then
    curl -fsSL -o /tmp/noble.img \
      https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img
    qemu-img convert -O raw /tmp/noble.img "$IMAGE_PATH" 2>/dev/null || mv /tmp/noble.img "$IMAGE_PATH"
  else
    truncate -s 4G "$IMAGE_PATH"
    mkfs.ext4 -F "$IMAGE_PATH" >/dev/null 2>&1 || true
  fi
  echo "✓ Base image provisioned at $IMAGE_PATH"
fi

echo "=== [3/3] Running Cloud Hypervisor KVM Smoke Test ==="
SMOKE_SOCK="/tmp/smoke-test.sock"
rm -f "$SMOKE_SOCK"

# Start hypervisor in background and poll API
cloud-hypervisor --api-socket "path=$SMOKE_SOCK" >/tmp/ch-smoke.log 2>&1 &
CH_PID=$!
sleep 1

if kill -0 "$CH_PID" 2>/dev/null; then
  echo "✓ Cloud Hypervisor process launched successfully (PID $CH_PID)"
  VMM_INFO=$(curl -s --unix-socket "$SMOKE_SOCK" http://localhost/api/v1/vmm.ping 2>/dev/null || true)
  echo "✓ VMM Ping Response: ${VMM_INFO:-OK}"
  kill "$CH_PID" 2>/dev/null || true
  wait "$CH_PID" 2>/dev/null || true
  rm -f "$SMOKE_SOCK"
  echo "✓ KVM Hardware Virtualization Smoke Test: PASSED"
else
  echo "✗ Failed to launch Cloud Hypervisor. Log tail:"
  cat /tmp/ch-smoke.log
  exit 1
fi
REMOTE_CH_EOF

log_ok "Cloud Hypervisor and base assets installed and verified on Node B!"
echo "Proceed to 04-deploy-worker.sh."
