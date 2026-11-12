#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 5: Verification of Azure Node B & Link Security
# Runs from Node A (Laptop) to verify:
# - WireGuard VPN handshake and ICMP ping
# - Worker API /health and /resources over private 10.100.0.2:8002
# - Security verification: port 8002 BLOCKED on public IP
# - Cgroups v2 delegation verification
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/common.sh"

if [ -f "$SCRIPT_DIR/node_b.env" ]; then
  source "$SCRIPT_DIR/node_b.env"
fi

PUBLIC_IP="${AZURE_NODE_B_PUBLIC_IP:-}"
NODE_B_WG_IP="$WG_NODE_B_IP"
WORKER_TOKEN=""

if [ -f "$REPO_ROOT/secrets.env" ]; then
  WORKER_TOKEN=$(grep -E '^PS023_TOKEN_NODE_B=' "$REPO_ROOT/secrets.env" | cut -d= -f2- | tr -d '"\047' || true)
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE} PS-023: Azure Node B & Hybrid Link Verification${NC}"
echo -e "${BLUE} Target Private Endpoint: http://${NODE_B_WG_IP}:${WORKER_PORT}/health${NC}"
if [ -n "$PUBLIC_IP" ]; then
  echo -e "${BLUE} Target Public IP:       ${PUBLIC_IP}${NC}"
fi
echo -e "${BLUE}======================================================================${NC}"
echo

FAILED=0

# 1. WireGuard Interface Status
log_info "[Check 1/5] Local WireGuard wg0 interface..."
if ip link show "$WG_INTERFACE" >/dev/null 2>&1; then
  LOCAL_IP=$(ip -4 addr show "$WG_INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "unknown")
  log_ok "WireGuard active (Local IP: $LOCAL_IP)"
else
  log_err "WireGuard interface '$WG_INTERFACE' is not active locally. Run: sudo wg-quick up $WG_INTERFACE"
  FAILED=$((FAILED + 1))
fi

# 2. ICMP Ping to Node B WireGuard IP
log_info "[Check 2/5] ICMP Ping to Node B ($NODE_B_WG_IP)..."
if ping -c 3 -W 2 "$NODE_B_WG_IP" >/dev/null 2>&1; then
  log_ok "Ping successful to $NODE_B_WG_IP"
else
  log_err "Ping failed to $NODE_B_WG_IP over WireGuard VPN."
  FAILED=$((FAILED + 1))
fi

# 3. HTTP Health Probe over WireGuard
log_info "[Check 3/5] Worker /health endpoint over VPN..."
HEALTH_RESP=$(curl -s -m 5 "http://${NODE_B_WG_IP}:${WORKER_PORT}/health" 2>/dev/null || true)
if echo "$HEALTH_RESP" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  log_ok "Worker healthy: $HEALTH_RESP"
else
  log_err "Failed to query worker health at http://${NODE_B_WG_IP}:${WORKER_PORT}/health (Received: '$HEALTH_RESP')"
  FAILED=$((FAILED + 1))
fi

# 4. Authenticated /resources Probe
if [ -n "$WORKER_TOKEN" ]; then
  log_info "[Check 4/5] Worker /resources endpoint over VPN..."
  RES_RESP=$(curl -s -m 5 -H "Authorization: Bearer $WORKER_TOKEN" "http://${NODE_B_WG_IP}:${WORKER_PORT}/resources" 2>/dev/null || true)
  if echo "$RES_RESP" | grep -q '"memory_schedulable_mb"'; then
    SCHED_RAM=$(echo "$RES_RESP" | grep -o '"memory_schedulable_mb": *[0-9]*' | cut -d: -f2 | tr -d ' ')
    CG_STATUS=$(echo "$RES_RESP" | grep -o '"cgroups_enabled": *[a-z]*' | cut -d: -f2 | tr -d ' ')
    log_ok "Resources retrieved: Schedulable RAM=${SCHED_RAM} MB | Cgroups=${CG_STATUS}"
  else
    log_warn "Worker /resources returned unexpected response: '$RES_RESP'"
  fi
fi

# 5. Security Check: Worker Port Must Be Blocked on Public IP
if [ -n "$PUBLIC_IP" ]; then
  log_info "[Check 5/5] Security: Verifying worker port $WORKER_PORT is blocked on Public IP ($PUBLIC_IP)..."
  if curl -s -m 3 "http://${PUBLIC_IP}:${WORKER_PORT}/health" >/dev/null 2>&1; then
    log_err "SECURITY VIOLATION: Worker port $WORKER_PORT is accessible via Public IP! Check Azure NSG rules."
    FAILED=$((FAILED + 1))
  else
    log_ok "Worker port $WORKER_PORT is unreachable via Public IP (Firewall Deny verified)."
  fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
  log_ok "======================================================================"
  log_ok " ALL VERIFICATION CHECKS PASSED: Azure Node B is Ready for Controller!"
  log_ok "======================================================================"
  echo "You can now join Azure Node B to the controller using:"
  echo "  export AZURE_HYBRID=1"
  echo "  bash bring-up.sh"
else
  log_err "Verification completed with $FAILED failures. Inspect logs above."
  exit 1
fi
