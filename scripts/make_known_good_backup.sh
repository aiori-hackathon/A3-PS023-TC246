#!/usr/bin/env bash
# ==============================================================================
# PS-023: Create Known-Good Cluster Component Backup
# ==============================================================================
# Creates a snapshot of controller/ and worker/ source trees inside
# ~/ps023_backups/known_good_<timestamp>/ and outputs the resulting path.
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

if [ "$DRY_RUN" -eq 1 ]; then
    echo "================================================================================"
    echo "PS-023: Known-Good Backup (DRY-RUN MODE)"
    echo "================================================================================"
    echo "Target Directory: ${TARGET_DIR}"
    echo "Source Controller: ${CTRL_SRC}"
    echo "Source Worker:     ${WORKER_SRC}"
    echo
    echo "Dry-run actions:"
    echo "  1. Would create directory: ${TARGET_DIR}"
    echo "  2. Would copy ${CTRL_SRC}/ -> ${TARGET_DIR}/controller/"
    echo "  3. Would copy ${WORKER_SRC}/ -> ${TARGET_DIR}/worker/"
    echo "Status: DRY-RUN COMPLETED (no files written)."
    echo "${TARGET_DIR}"
    exit 0
fi

mkdir -p "${TARGET_DIR}/controller" "${TARGET_DIR}/worker"

rsync -a --exclude '__pycache__' --exclude '*.pyc' "${CTRL_SRC}/" "${TARGET_DIR}/controller/"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "${WORKER_SRC}/" "${TARGET_DIR}/worker/"

echo "================================================================================"
echo "PS-023: Known-Good Backup Successfully Created"
echo "================================================================================"
echo "Backup Path: ${TARGET_DIR}"
echo "${TARGET_DIR}"
