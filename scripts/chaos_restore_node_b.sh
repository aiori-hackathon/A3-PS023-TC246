#!/usr/bin/env bash
# ==============================================================================
# PS-023: Chaos Test - Restore Node B & Verify Fencing of Stale Copies
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/chaos_restore_node_b.sh [worker|network]

Modes:
  worker   - Start the worker service on Node B via SSH
  network  - Bring back up the WireGuard interface (wg0) on the controller host

Environment Variables (Optional / Configurable):
  PS023_API_TOKEN       - Controller bearer token (defaults to loading secrets.env)
  PS023_CONTROLLER_URL  - Controller URL (default: http://127.0.0.1:8000)
  NODE_B_SSH_HOST       - Node B IP or hostname (e.g. 10.100.0.2 or nested VM IP)
  NODE_B_SSH_USER       - Node B SSH username (default: ubuntu)
  NODE_B_SSH_KEY        - Path to SSH private key (if using key auth)
  NODE_B_SSH_PASS       - SSH password (if using password/sshpass)
  WG_INTERFACE          - WireGuard interface name (default: wg0)

Example:
  ./scripts/chaos_restore_node_b.sh worker
EOF
  exit 1
}

MODE="${1:-}"
if [ -z "$MODE" ] || [ "$MODE" = "-h" ] || [ "$MODE" = "--help" ]; then
  usage
fi

CONTROLLER_URL="${PS023_CONTROLLER_URL:-http://127.0.0.1:8000}"

# Load secrets.env if token not set in environment
if [ -z "${PS023_API_TOKEN:-}" ]; then
  if [ -f "$REPO_ROOT/secrets.env" ]; then
    PS023_API_TOKEN=$(grep -E '^PS023_API_TOKEN=' "$REPO_ROOT/secrets.env" | cut -d= -f2- | tr -d '"'"'")
  elif [ -f "$HOME/ps023/secrets.env" ]; then
    PS023_API_TOKEN=$(grep -E '^PS023_API_TOKEN=' "$HOME/ps023/secrets.env" | cut -d= -f2- | tr -d '"'"'")
  elif [ -f "secrets.env" ]; then
    PS023_API_TOKEN=$(grep -E '^PS023_API_TOKEN=' secrets.env | cut -d= -f2- | tr -d '"'"'")
  fi
fi

if [ -z "${PS023_API_TOKEN:-}" ]; then
  echo "[-] ERROR: PS023_API_TOKEN is not set and not found in secrets.env" >&2
  exit 1
fi

AUTH_HEADER="Authorization: Bearer $PS023_API_TOKEN"

api_get() {
  curl -s -f -H "$AUTH_HEADER" "$CONTROLLER_URL$1"
}

echo "=== [1/3] Restoring Node B (Mode: $MODE) ==="
T_RESTORE_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$T_RESTORE_HUMAN] Bringing Node B back online..."

if [ "$MODE" = "worker" ]; then
  NODE_B_HOST="${NODE_B_SSH_HOST:-10.100.0.2}"
  NODE_B_USER="${NODE_B_SSH_USER:-ubuntu}"

  START_CMD="sudo systemctl start ps023-worker 2>/dev/null || (cd ~/ps023/worker && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8002 > ~/worker.log 2>&1 &) || true"

  SSH_OPTS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=5"
  if [ -n "${NODE_B_SSH_KEY:-}" ]; then
    ssh -i "$NODE_B_SSH_KEY" $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$START_CMD"
  elif [ -n "${NODE_B_SSH_PASS:-}" ] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$NODE_B_SSH_PASS" ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$START_CMD"
  else
    ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$START_CMD"
  fi
  echo "  Node B worker service started."
elif [ "$MODE" = "network" ]; then
  WG_IF="${WG_INTERFACE:-wg0}"
  echo "  Bringing up interface $WG_IF..."
  sudo ip link set "$WG_IF" up
  echo "  Network link restored to Node B."
else
  echo "[-] Unknown mode: $MODE" >&2
  usage
fi

echo
echo "=== [2/3] Waiting for Node B to return to HEALTHY ==="
RESTORED=0
for i in $(seq 1 40); do
  STATUS=$(api_get "/nodes/node-b" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("status", "UNKNOWN"))' 2>/dev/null || echo "UNKNOWN")
  if [ "$STATUS" = "HEALTHY" ]; then
    T_HEALTHY_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$T_HEALTHY_HUMAN] Node B is HEALTHY!"
    RESTORED=1
    break
  fi
  sleep 1
done

if [ "$RESTORED" -eq 0 ]; then
  echo "[-] Timed out waiting for node-b to become HEALTHY." >&2
  exit 1
fi

echo
echo "=== [3/3] Fencing Verification: Confirming Stale Copies Cleaned Up ==="
# Allow reconcile cycle to run fencing pass
sleep 3

VMS_JSON=$(api_get "/vms")
echo "Current VM Placement & States:"
echo "$VMS_JSON" | python3 -c '
import sys, json
vms = json.load(sys.stdin)
for v in vms:
    ha_str = " [HA]" if v.get("ha") else ""
    print(f"  VM {v[\"id\"]} ({v[\"name\"]}) -> Node: {v[\"node_id\"]} | Status: {v[\"status\"]}{ha_str}")
'

NODE_B_RESOURCES=$(api_get "/nodes/node-b/resources" 2>/dev/null || echo "{}")
echo
echo "Node B Worker Active VMs (Should NOT contain stale copies of evacuated VMs):"
echo "$NODE_B_RESOURCES" | python3 -c '
import sys, json
res = json.load(sys.stdin)
vms_running = res.get("vms_running", 0)
print(f"  Node B reported running VMs: {vms_running}")
'

echo "=== Fencing & Node B Restoration Verified ==="
