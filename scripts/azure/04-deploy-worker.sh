#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 4: Deploy Worker Service on Node B
# Synchronizes worker Python code, creates virtualenv, installs systemd service:
# - Delegate=yes (cgroups v2 subtree control)
# - DelegateSubgroup=service (leaf cgroup separation for zero-downtime restarts)
# - KillMode=process (VMs survive worker restart)
# - Binds strictly to 10.100.0.2:8002 (WireGuard mode) or 127.0.0.1:8002 (SSH mode)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/common.sh"

if [ -f "$SCRIPT_DIR/node_b.env" ]; then
  source "$SCRIPT_DIR/node_b.env"
fi

# Resolve worker source directory: support src/worker (submit repo) and worker/ (live repo)
WORKER_SRC=""
for cand in "$REPO_ROOT/src/worker" "$REPO_ROOT/worker" "$SCRIPT_DIR/../../src/worker" "$SCRIPT_DIR/../../worker"; do
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

# Determine worker bind mode: default is 127.0.0.1. WireGuard mode sets 10.100.0.2 explicitly.
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
  echo "=== [DRY RUN] 04-deploy-worker.sh ==="
  echo "REPO_ROOT: $REPO_ROOT"
  echo "SCRIPT_DIR: $SCRIPT_DIR"
  echo "Resolved source path: $WORKER_SRC"
  echo "Worker bind host: $WORKER_BIND"
  echo "Files that would be copied to Node B (/opt/ps023-worker/worker/):"
  ls -1 "$WORKER_SRC"
  exit 0
fi

NODE_B_HOST=""
for arg in "$@"; do
  if [[ "$arg" != --* ]] && [ -n "$arg" ]; then
    NODE_B_HOST="$arg"
    break
  fi
done
if [ -z "$NODE_B_HOST" ]; then
  NODE_B_HOST="${AZURE_NODE_B_PUBLIC_IP:-}"
fi

if [ -z "$NODE_B_HOST" ]; then
  log_err "Missing Node B host IP. Pass it as \$1 or define in scripts/azure/node_b.env."
  exit 1
fi

SSH_USER="${AZURE_ADMIN_USER:-ubuntu}"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

# Load Worker Token from secrets.env safely
WORKER_TOKEN=""
VM_PASS=""
if [ -f "$REPO_ROOT/secrets.env" ]; then
  WORKER_TOKEN=$(grep -E '^PS023_TOKEN_NODE_B=' "$REPO_ROOT/secrets.env" | cut -d= -f2- | tr -d '"\047' || true)
  VM_PASS=$(grep -E '^PS023_VM_PASSWORD=' "$REPO_ROOT/secrets.env" | cut -d= -f2- | tr -d '"\047' || true)
fi

log_info "Synchronizing worker codebase to Azure Node B ($NODE_B_HOST)..."

# Sync worker files
tar -C "$WORKER_SRC" -cf - . | ssh $SSH_OPTS "$SSH_USER@$NODE_B_HOST" '
sudo mkdir -p /opt/ps023-worker/worker
sudo chown -R $USER:$USER /opt/ps023-worker
tar -xf - -C /opt/ps023-worker/worker
cp -rn /opt/ps023-worker/worker/* /opt/ps023-worker/ 2>/dev/null || true
'

ssh $SSH_OPTS "$SSH_USER@$NODE_B_HOST" "bash -s -- '$WORKER_TOKEN' '$VM_PASS' '$WORKER_BIND'" << 'REMOTE_DEPLOY_EOF'
set -euo pipefail
WORKER_TOKEN="$1"
VM_PASS="$2"
WORKER_BIND="${3:-127.0.0.1}"
if [ -z "$WORKER_BIND" ]; then
  WORKER_BIND="127.0.0.1"
fi

if [ "$WORKER_BIND" = "10.100.0.2" ]; then
  WG_WANTS="Wants=network-online.target wg-quick@wg0.service"
else
  WG_WANTS="Wants=network-online.target"
fi

WORKER_DIR="/opt/ps023-worker"
VENV_DIR="$WORKER_DIR/venv"

echo "=== [1/3] Setting up Python Virtual Environment ==="
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -U pip
"$VENV_DIR/bin/pip" install -q fastapi uvicorn httpx psutil

echo "=== [2/3] Writing Environment Configuration ==="
cat > "$WORKER_DIR/worker.env" << EOF
PS023_NODE_ID=node-b
PS023_WORKER_BIND=$WORKER_BIND
PS023_WORKER_TOKEN=$WORKER_TOKEN
PS023_VM_PASSWORD=$VM_PASS
PS023_VM_ROOT=$WORKER_DIR/vms
PS023_BASE_IMAGE=$WORKER_DIR/images/ubuntu-24-04.raw
PS023_KERNEL=$WORKER_DIR/kernel/vmlinux.bin
PS023_SUBNET=192.168.200.0/24
PS023_SLOT_START=0
PS023_SLOT_COUNT=8
EOF
chmod 600 "$WORKER_DIR/worker.env"

echo "=== [3/3] Installing Systemd Service (Delegate=yes, KillMode=process) ==="
sudo bash -c "cat > /etc/systemd/system/ps023-worker.service" << EOF
[Unit]
Description=PS-023 Cloud Hypervisor Worker Node B
After=network.target network-online.target wg-quick@wg0.service
$WG_WANTS

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$WORKER_DIR/worker
EnvironmentFile=$WORKER_DIR/worker.env
ExecStart=$VENV_DIR/bin/python3 -m uvicorn main:app --host $WORKER_BIND --port 8002
Restart=always
RestartSec=3
KillMode=process
Delegate=yes
DelegateSubgroup=service
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ps023-worker.service
sudo systemctl restart ps023-worker.service || echo "Note: Service will fully listen once WireGuard wg0 ($WORKER_BIND) is up."
echo "✓ ps023-worker.service configured and enabled"
REMOTE_DEPLOY_EOF

log_ok "Worker service successfully deployed on Azure Node B!"
echo "Proceed to 05-verify-node-b.sh to test connectivity and cgroups."
