#!/usr/bin/env bash
# ==============================================================================
# PS-023: Safe Sync from Repo (~/ps023-submit) to Live System (~/ps023)
# ==============================================================================
set -euo pipefail

REPO_DIR="${HOME}/ps023-submit"
LIVE_DIR="${HOME}/ps023"
BACKUP_BASE="${HOME}/ps023_backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_BASE}/backup_${TIMESTAMP}"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  DRY_RUN=1
fi

echo "================================================================="
echo "PS-023 Sync: Repo (source of truth) -> Live System"
echo "Source repo: ${REPO_DIR}"
echo "Live target: ${LIVE_DIR}"
echo "Scope: controller/ and worker/ ONLY"
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "MODE: DRY-RUN (rsync -acvn, no changes made)"
else
  echo "MODE: REAL EXECUTION"
fi
echo "================================================================="

# Strict virtualenv python check: use ~/ps023/.venv/bin/python, fail if missing
PYTHON_BIN="${LIVE_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: Virtualenv Python missing or not executable at: ${PYTHON_BIN}" >&2
  exit 1
fi

# Token handling: notice printed when fallback validation token is used
if [[ -z "${PS023_API_TOKEN:-}" ]]; then
  echo "NOTICE: PS023_API_TOKEN is unset in environment; using temporary validation token for import test."
  CHECK_API_TOKEN="sync_validation_token_0123456789"
else
  CHECK_API_TOKEN="${PS023_API_TOKEN}"
fi

if [[ -z "${PS023_WORKER_TOKEN:-}" ]]; then
  echo "NOTICE: PS023_WORKER_TOKEN is unset in environment; using temporary validation token for import test."
  CHECK_WORKER_TOKEN="sync_validation_token_0123456789"
else
  CHECK_WORKER_TOKEN="${PS023_WORKER_TOKEN}"
fi

# Common excludes for controller and worker
EXCLUDES=(
  --exclude="secrets.env"
  --exclude="controller.db"
  --exclude="controller.db-*"
  --exclude="*.db"
  --exclude=".venv"
  --exclude=".venv/"
  --exclude=".venv-clean"
  --exclude=".venv-clean/"
  --exclude="logs"
  --exclude="logs/"
  --exclude="vms"
  --exclude="vms/"
  --exclude="vms-b"
  --exclude="vms-b/"
  --exclude="node_modules"
  --exclude="node_modules/"
  --exclude="__pycache__"
  --exclude="__pycache__/"
  --exclude="*.pyc"
  --exclude=".pytest_cache"
  --exclude=".pytest_cache/"
  --exclude="*.sock*"
)

# Step 1: Pre-flight import check against REPO copy before any backup or sync
echo "[1/4] Running Python import check against REPO copy (${REPO_DIR}/src) using ${PYTHON_BIN}..."
PS023_API_TOKEN="${CHECK_API_TOKEN}" \
PYTHONPATH="${REPO_DIR}/src/controller:${REPO_DIR}/src" \
  "${PYTHON_BIN}" -c "
import main
import vm_service
import scheduler
import database
import auth
import worker_client
print('  [OK] Repo controller module imports verified')
"

PS023_WORKER_TOKEN="${CHECK_WORKER_TOKEN}" \
PYTHONPATH="${REPO_DIR}/src/worker:${REPO_DIR}/src" \
  "${PYTHON_BIN}" -c "
import main
import vm_manager
import cgroup_manager
import cloud_hypervisor
print('  [OK] Repo worker module imports verified')
"

if [[ ${DRY_RUN} -eq 1 ]]; then
  echo ""
  echo "[2/4] DRY-RUN: Simulating backup creation (target: ${BACKUP_DIR})..."
  echo ""
  echo "[3/4] DRY-RUN: Mapping 1: src/controller/ -> ~/ps023/controller/"
  rsync -acvn "${EXCLUDES[@]}" "${REPO_DIR}/src/controller/" "${LIVE_DIR}/controller/"
  echo ""
  echo "[3/4] DRY-RUN: Mapping 2: src/worker/ -> ~/ps023/worker/"
  rsync -acvn "${EXCLUDES[@]}" "${REPO_DIR}/src/worker/" "${LIVE_DIR}/worker/"
  echo ""
  echo "[4/4] DRY-RUN: Real rollback command when executed live will be:"
  echo "-----------------------------------------------------------------"
  echo "rsync -ac \"${BACKUP_DIR}/controller/\" \"${LIVE_DIR}/controller/\" && \\"
  echo "rsync -ac \"${BACKUP_DIR}/worker/\" \"${LIVE_DIR}/worker/\""
  echo "-----------------------------------------------------------------"
  echo "Dry run complete. No files were modified."
  exit 0
fi

# ============================ REAL EXECUTION ============================
echo ""
echo "[2/4] Creating timestamped backup of live controller and worker..."
mkdir -p "${BACKUP_DIR}/controller" "${BACKUP_DIR}/worker"

if [[ -d "${LIVE_DIR}/controller" ]]; then
  rsync -a "${EXCLUDES[@]}" "${LIVE_DIR}/controller/" "${BACKUP_DIR}/controller/"
fi
if [[ -d "${LIVE_DIR}/worker" ]]; then
  rsync -a "${EXCLUDES[@]}" "${LIVE_DIR}/worker/" "${BACKUP_DIR}/worker/"
fi
echo "  -> Backup created successfully at: ${BACKUP_DIR}"

echo ""
echo "[3/4] Executing rsync -ac (checksum content compare) for controller and worker..."
echo "  -> Syncing src/controller/ -> ~/ps023/controller/ ..."
rsync -acv "${EXCLUDES[@]}" "${REPO_DIR}/src/controller/" "${LIVE_DIR}/controller/"

echo "  -> Syncing src/worker/ -> ~/ps023/worker/ ..."
rsync -acv "${EXCLUDES[@]}" "${REPO_DIR}/src/worker/" "${LIVE_DIR}/worker/"
echo "  -> Controller and worker synchronized."

echo ""
echo "[4/4] Rollback reference:"
echo "================================================================="
echo "If rollback is required, run:"
echo "rsync -ac \"${BACKUP_DIR}/controller/\" \"${LIVE_DIR}/controller/\" && \\"
echo "rsync -ac \"${BACKUP_DIR}/worker/\" \"${LIVE_DIR}/worker/\""
echo "================================================================="
echo "Sync completed successfully."
