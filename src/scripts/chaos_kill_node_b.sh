#!/usr/bin/env bash
# ==============================================================================
# PS-023: Chaos Test - Simulate Node B Failure (Centerpiece Demo)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/chaos_kill_node_b.sh [worker|worker-preserve-vms|network]

Modes:
  worker               - systemctl stop ps023-worker AND kill all cloud-hypervisor
                         processes on node B (simulated node failure, VMs gone).
                         Note: uses systemctl stop because Restart=always would otherwise
                         restart the worker within 3 s.
  worker-preserve-vms  - systemctl stop only (VMs keep running; tests fencing on return).
  network              - Take down the WireGuard interface (wg0) on the controller host

Environment Variables (Optional / Configurable):
  PS023_API_TOKEN       - Controller bearer token (defaults to loading secrets.env)
  PS023_CONTROLLER_URL  - Controller URL (default: http://127.0.0.1:8000)
  NODE_B_SSH_HOST       - Node B IP or hostname (e.g. 10.100.0.2 or nested VM IP)
  NODE_B_SSH_USER       - Node B SSH username (default: ubuntu)
  NODE_B_SSH_KEY        - Path to SSH private key (if using key auth)
  NODE_B_SSH_PASS       - SSH password (if using password/sshpass)
  WG_INTERFACE          - WireGuard interface name (default: wg0)

Example:
  ./scripts/chaos_kill_node_b.sh worker
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

# 1. Inspect cluster state before chaos
echo "=== [1/4] Baseline Cluster State ==="
echo "Nodes:"
api_get "/nodes" | python3 -c '
import sys, json
nodes = json.load(sys.stdin)
for n in nodes:
    print("  * Node %s: status=%s schedulable_mb=%s vms_running=%s" % (n.get("id"), n.get("status"), n.get("memory_schedulable_mb"), n.get("vms_running", 0)))
'

echo "VMs:"
api_get "/vms" | python3 -c '
import sys, json
vms = json.load(sys.stdin)
if not vms:
    print("  (no VMs deployed)")
for v in vms:
    ha_str = "[HA]" if v.get("ha") else "[NON-HA]"
    print("  * %s (%s) %s: Node=%s Status=%s IP=%s" % (v.get("id"), v.get("name"), ha_str, v.get("node_id"), v.get("status"), v.get("ip_address")))
'

# 2. Inject failure based on selected mode
echo
echo "=== [2/4] Injecting Failure (Mode: $MODE) ==="
T_KILL=$(date +%s.%N)
T_KILL_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$T_KILL_HUMAN] Executing failure injection..."

if [ "$MODE" = "worker" ]; then
  NODE_B_HOST="${NODE_B_SSH_HOST:-10.100.0.2}"
  NODE_B_USER="${NODE_B_SSH_USER:-ubuntu}"

  # Mode 'worker': Stop worker and kill all cloud-hypervisor processes (simulated node failure, VMs gone)
  # Uses systemctl stop because Restart=always would otherwise restart the worker in 3 s.
  # Uses [c]loud-hypervisor bracket pattern so pkill does not match its own remote ssh shell.
  KILL_CMD="sudo systemctl stop ps023-worker && sudo pkill -9 -f '[c]loud-hypervisor' || true"

  SSH_OPTS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=5"
  if [ -n "${NODE_B_SSH_KEY:-}" ]; then
    ssh -i "$NODE_B_SSH_KEY" $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  elif [ -n "${NODE_B_SSH_PASS:-}" ] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$NODE_B_SSH_PASS" ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  else
    ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  fi
  echo "  Node B worker stopped and all cloud-hypervisor processes killed (VMs gone)."
elif [ "$MODE" = "worker-preserve-vms" ]; then
  NODE_B_HOST="${NODE_B_SSH_HOST:-10.100.0.2}"
  NODE_B_USER="${NODE_B_SSH_USER:-ubuntu}"

  # Mode 'worker-preserve-vms': systemctl stop only (VMs keep running; tests fencing on return)
  KILL_CMD="sudo systemctl stop ps023-worker"

  SSH_OPTS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=5"
  if [ -n "${NODE_B_SSH_KEY:-}" ]; then
    ssh -i "$NODE_B_SSH_KEY" $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  elif [ -n "${NODE_B_SSH_PASS:-}" ] && command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$NODE_B_SSH_PASS" ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  else
    ssh $SSH_OPTS "$NODE_B_USER@$NODE_B_HOST" "$KILL_CMD"
  fi
  echo "  Node B worker stopped. Cloud-hypervisor processes remain running to test recovery fencing."
elif [ "$MODE" = "network" ]; then
  WG_IF="${WG_INTERFACE:-wg0}"
  echo "  Taking down interface $WG_IF..."
  sudo ip link set "$WG_IF" down
  echo "  Network severed to Node B."
else
  echo "[-] Unknown mode: $MODE" >&2
  usage
fi

# 3. Wait for controller to mark node-b UNHEALTHY
echo
echo "=== [3/4] Detection: Waiting for Node B UNHEALTHY transition ==="
DETECTED=0
for i in $(seq 1 40); do
  STATUS=$(api_get "/nodes/node-b" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("status", "UNKNOWN"))' 2>/dev/null || echo "UNKNOWN")
  if [ "$STATUS" = "UNHEALTHY" ]; then
    T_DETECT=$(date +%s.%N)
    T_DETECT_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
    DIFF=$(echo "$T_DETECT - $T_KILL" | bc -l)
    printf "[%s] Controller marked node-b as UNHEALTHY (detection delay: %.2fs)\n" "$T_DETECT_HUMAN" "$DIFF"
    DETECTED=1
    break
  fi
  sleep 1
done

if [ "$DETECTED" -eq 0 ]; then
  echo "[-] Timed out waiting for node-b to become UNHEALTHY." >&2
  exit 1
fi

# 4. Monitor auto-evacuation of HA VMs
echo
echo "=== [4/4] Self-Healing: Monitoring Auto-Evacuation to Node A ==="
EVACUATED=0
for i in $(seq 1 60); do
  VMS_JSON=$(api_get "/vms")
  PENDING_EVAC=$(echo "$VMS_JSON" | python3 -c '
import sys, json
vms = json.load(sys.stdin)
ha_vms = [v for v in vms if v.get("ha")]
still_evacuating = [v for v in ha_vms if v.get("node_id") != "node-a" or v.get("status") != "RUNNING"]
print(len(still_evacuating))
')

  if [ "$PENDING_EVAC" -eq 0 ]; then
    T_EVAC=$(date +%s.%N)
    T_EVAC_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
    TOTAL_RECOVERY=$(echo "$T_EVAC - $T_KILL" | bc -l)
    printf "\n[%s] ALL HA VMs Successfully Evacuated to node-a! Total recovery time: %.2fs\n\n" "$T_EVAC_HUMAN" "$TOTAL_RECOVERY"

    echo "Evacuated VM details:"
    echo "$VMS_JSON" | python3 -c '
import sys, json
vms = json.load(sys.stdin)
for v in vms:
    if v.get("ha"):
        rec = v.get("recovery_time_s", "n/a")
        print("  * %s (%s) -> Node: %s | Status: %s | IP: %s | Recovery: %ss" % (v.get("id"), v.get("name"), v.get("node_id"), v.get("status"), v.get("ip_address"), rec))
'
    EVACUATED=1
    break
  fi
  printf "."
  sleep 1
done

if [ "$EVACUATED" -eq 0 ]; then
  echo
  echo "[-] Timed out waiting for HA VMs to recover. Current VM states:"
  api_get "/vms"
  exit 1
fi

echo
echo "Latest Structured Decisions:"
api_get "/decisions?limit=3" | python3 -c '
import sys, json
for d in json.load(sys.stdin):
    print(f"  [{d.get(\"vm_id\", \"cluster\")}] {d.get(\"reason\")}")
'
echo "=== Self-Healing Verification Complete ==="
