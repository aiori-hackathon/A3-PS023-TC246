#!/usr/bin/env bash
# ==============================================================================
# PS-023: Create Known-Good Cluster Component Backup
# ==============================================================================
# Creates a snapshot of controller/ and worker/ source trees inside
# ~/ps023_backups/known_good_<timestamp>/, records kernel SHA-256 hashes,
# and records nested Node B disk path and hash (without re-copying the 20 GB file).
# Supports --dry-run to inspect target directory and files without copying.
# ==============================================================================

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
fi

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_BASE="$HOME/ps023_backups"
TARGET_DIR="${BACKUP_BASE}/known_good_${TIMESTAMP}"

# Determine source repository directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Verify controller and worker directories exist
if [ -d "${REPO_DIR}/controller" ]; then
    CTRL_SRC="${REPO_DIR}/controller"
elif [ -d "${REPO_DIR}/src/controller" ]; then
    CTRL_SRC="${REPO_DIR}/src/controller"
else
    echo "ERROR: controller directory not found in ${REPO_DIR}" >&2
    exit 1
fi

if [ -d "${REPO_DIR}/worker" ]; then
    WORKER_SRC="${REPO_DIR}/worker"
elif [ -d "${REPO_DIR}/src/worker" ]; then
    WORKER_SRC="${REPO_DIR}/src/worker"
else
    echo "ERROR: worker directory not found in ${REPO_DIR}" >&2
    exit 1
fi

KERNEL_DIR="${REPO_DIR}/lab/kernel"
DISK_PATH="${REPO_DIR}/outer/disk.raw"
BACKUP_DISK="${BACKUP_BASE}/nested_node_b_disk_20261115.raw"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "================================================================================"
    echo "PS-023: Known-Good Backup (DRY-RUN MODE)"
    echo "================================================================================"
    echo "Target Directory: ${TARGET_DIR}"
    echo "Source Controller: ${CTRL_SRC}"
    echo "Source Worker:     ${WORKER_SRC}"
    echo "Kernel Directory:  ${KERNEL_DIR}"
    echo "Nested Node B Disk: ${DISK_PATH}"
    echo
    echo "Dry-run actions:"
    echo "  1. Would create directory: ${TARGET_DIR}"
    echo "  2. Would copy ${CTRL_SRC}/ -> ${TARGET_DIR}/controller/"
    echo "  3. Would copy ${WORKER_SRC}/ -> ${TARGET_DIR}/worker/"
    echo "  4. Would record kernel SHA-256 hashes"
    echo "  5. Would record nested Node B disk path and SHA-256 hash"
    echo "Status: DRY-RUN COMPLETED (no files written)."
    echo "${TARGET_DIR}"
    exit 0
fi

mkdir -p "${TARGET_DIR}/controller" "${TARGET_DIR}/worker"

rsync -a --exclude '__pycache__' --exclude '*.pyc' "${CTRL_SRC}/" "${TARGET_DIR}/controller/"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "${WORKER_SRC}/" "${TARGET_DIR}/worker/"

MANIFEST="${TARGET_DIR}/manifest.txt"
echo "=== PS-023 Known-Good Backup Manifest ($TIMESTAMP) ===" > "$MANIFEST"

if [ -d "$KERNEL_DIR" ]; then
    echo >> "$MANIFEST"
    echo "--- Kernel Binaries (lab/kernel) ---" >> "$MANIFEST"
    sha256sum "$KERNEL_DIR"/vmlinux*.bin* >> "$MANIFEST" 2>/dev/null || true
fi

if [ -f "$DISK_PATH" ]; then
    echo >> "$MANIFEST"
    echo "--- Nested Node B Disk ---" >> "$MANIFEST"
    echo "Path: $DISK_PATH" >> "$MANIFEST"
    sha256sum "$DISK_PATH" >> "$MANIFEST"
    if [ ! -f "$BACKUP_DISK" ]; then
        echo "Copying baseline disk backup to ${BACKUP_DISK}..."
        cp --sparse=always "$DISK_PATH" "$BACKUP_DISK"
    fi
    echo "Baseline Backup Reference: $BACKUP_DISK" >> "$MANIFEST"
fi

echo "================================================================================"
echo "PS-023: Known-Good Backup Successfully Created"
echo "================================================================================"
echo "Backup Path: ${TARGET_DIR}"
echo "Manifest:    ${MANIFEST}"
cat "$MANIFEST"
echo "================================================================================"
echo "${TARGET_DIR}"
