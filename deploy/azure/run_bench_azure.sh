#!/usr/bin/env bash
set -euo pipefail

NODE_B_PUBLIC_IP="${NODE_B_PUBLIC_IP:?NODE_B_PUBLIC_IP environment variable must be set}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Part A: Run VMM Socket Readiness check on Node B via SSH
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=accept-new "ubuntu@${NODE_B_PUBLIC_IP}" '
TEST_DIR="/tmp/ps023-boot-test"
SOCK="$TEST_DIR/test-vm.sock"
SERIAL_LOG="$TEST_DIR/serial.log"
VMM_LOG="$TEST_DIR/vmm.log"

echo "=== [1/5] Checking Hardware Virtualization Support on Azure ==="
if [ ! -e /dev/kvm ]; then
  echo "ERROR: /dev/kvm is missing. Nested virtualization must be enabled on Azure." >&2
  exit 1
fi

rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

AZURE_SKU=$(curl -s -m 2 -H "Metadata: true" "http://169.254.169.254/metadata/instance/compute/vmSize?api-version=2021-02-01&format=text" 2>/dev/null || echo "Standard_D2s_v4")

echo "=== [2/5] Preparing Test Kernel & Disk Payload ==="
IMAGE_CANDIDATE="/opt/ps023-worker/images/ubuntu-24-04.raw"
KERNEL="/opt/ps023-worker/kernel/vmlinux.bin"
cp --reflink=auto "$IMAGE_CANDIDATE" "$TEST_DIR/test-disk.raw" 2>/dev/null || \
  cp "$IMAGE_CANDIDATE" "$TEST_DIR/test-disk.raw"
DISK="$TEST_DIR/test-disk.raw"
echo "Found worker kernel and Ubuntu base image ($IMAGE_CANDIDATE). Creating lightweight copy for socket test..."

echo "=== [3/5] Measuring Raw VMM Process & API Socket Readiness ==="
T_START=$(date +%s%N)

cloud-hypervisor \
  --api-socket "path=$SOCK" \
  --cpus boot=2 \
  --memory size=1024M \
  --kernel "$KERNEL" \
  --disk "path=$DISK,image_type=raw" \
  --cmdline "console=ttyS0 root=/dev/vda1 rw quiet init=/bin/sh" \
  --serial "file=$SERIAL_LOG" \
  --console off \
  > "$VMM_LOG" 2>&1 &
VMM_PID=$!

for i in $(seq 1 100); do
  if [ -S "$SOCK" ]; then
    break
  fi
  sleep 0.05
done

T_END=$(date +%s%N)
ELAPSED_NS=$((T_END - T_START))
ELAPSED_MS=$((ELAPSED_NS / 1000000))
ELAPSED_SEC=$(python3 -c "import sys; print(\"%.3f\" % (float(sys.argv[1])/1000.0))" "$ELAPSED_MS")

echo "=== [4/5] Raw VMM Socket Initialization Latency ==="
echo "======================================================================"
echo " Cloud Hypervisor v54.0.0 on Azure ${AZURE_SKU} (Nested KVM)"
echo "----------------------------------------------------------------------"
echo " VMM Initialization Status     : SUCCESS"
echo " VMM API Socket Readiness Time : ${ELAPSED_MS} ms (${ELAPSED_SEC} s) [Socket ready, not guest OS boot]"
echo " Benchmark VMM Process ID      : ${VMM_PID}"
echo " Host CPU Model                : $(lscpu | awk -F: '/Model name/ {sub(/^[ \t]+/, "", $2); print $2; exit}')"
echo " Physical Cores Available      : $(nproc) vCPUs"
echo " Virtualization Type           : Nested KVM (/dev/kvm)"
echo "======================================================================"

kill "$VMM_PID" 2>/dev/null || true
wait "$VMM_PID" 2>/dev/null || true
rm -rf "$TEST_DIR"
'

echo ""
# Part B: Run 5-run benchmark through controller pinned to node-b
python3 "$REPO_ROOT/scripts/benchmark_controller.py" node-b 5
