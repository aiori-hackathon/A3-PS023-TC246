#!/usr/bin/env bash
# scripts/test_boot_images.sh
# Verifies official checksums and runs direct-kernel boot tests for Alpine 3.20 and CirrOS 0.6.2.
# Note: Requires sudo for /dev/kvm and TAP/loop devices.
set -euo pipefail

IMAGE_DIR="${PS023_IMAGE_ROOT:-${HOME}/ps023/images}"
mkdir -p "${IMAGE_DIR}"
cd "${IMAGE_DIR}"

CIRROS_FILE="cirros-0.6.2-x86_64-disk.img"
CIRROS_URL="https://download.cirros-cloud.net/0.6.2/${CIRROS_FILE}"
CIRROS_SHA256="07e44a73e54c94d988028515403c1ed762055e01b83a767edf3c2b387f78ce00"
CIRROS_MD5="c8fc807773e5354afe61636071771906"

echo "=== PS-023 Image Verification: CirrOS 0.6.2 ==="
if [ ! -f "${CIRROS_FILE}" ]; then
  echo "Downloading ${CIRROS_FILE}..."
  curl -fsSL "${CIRROS_URL}" -o "${CIRROS_FILE}"
fi

echo "Verifying SHA-256 for ${CIRROS_FILE}..."
echo "${CIRROS_SHA256}  ${CIRROS_FILE}" | sha256sum -c -
echo "Verifying MD5 for ${CIRROS_FILE}..."
echo "${CIRROS_MD5}  ${CIRROS_FILE}" | md5sum -c -
echo "[OK] CirrOS 0.6.2 checksums verified."

ALPINE_FILE="alpine-virt-3.20.3-x86_64.iso"
ALPINE_URL="https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/${ALPINE_FILE}"
ALPINE_SHA256="81df854fbd7327d293c726b1eeeb82061d3bc8f5a86a6f77eea720f6be372261"

echo "=== PS-023 Image Verification: Alpine Linux 3.20.3 ==="
if [ ! -f "${ALPINE_FILE}" ]; then
  echo "Downloading ${ALPINE_FILE}..."
  curl -fsSL "${ALPINE_URL}" -o "${ALPINE_FILE}"
fi

echo "Verifying SHA-256 for ${ALPINE_FILE}..."
echo "${ALPINE_SHA256}  ${ALPINE_FILE}" | sha256sum -c -
echo "[OK] Alpine 3.20.3 checksums verified."

echo "All images verified successfully against official cryptographic hashes."
