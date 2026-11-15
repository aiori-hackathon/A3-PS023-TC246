#!/usr/bin/env bash
# ==============================================================================
# PS-023: WireGuard & Worker Connectivity Verification Script
# Runs from Node A (Laptop) to verify tunnel, handshake, and worker HTTP health
# ==============================================================================
set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED=0
NODE_B_IP="10.100.0.2"
WORKER_PORT="8002"
HEALTH_URL="http://${NODE_B_IP}:${WORKER_PORT}/health"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE} PS-023: Verifying Hybrid Cluster Link (Node A -> Node B AWS EC2)${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo

# ------------------------------------------------------------------------------
# Check 1: Ping 10.100.0.2
# ------------------------------------------------------------------------------
echo -n "[Check 1/3] ICMP Ping to Node B (${NODE_B_IP})... "
if ping -c 3 -W 2 "$NODE_B_IP" >/dev/null 2>&1; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL${NC}"
  echo -e "  ${YELLOW}-> Hint: WireGuard tunnel is down or packets are blocked by security group.${NC}"
  echo -e "     Ensure 'wg-quick up wg0' is active on both sides and UDP 51820 is open on AWS."
  FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# Check 2: WireGuard Handshake
# ------------------------------------------------------------------------------
echo -n "[Check 2/3] WireGuard Handshake Verification... "
if command -v sudo >/dev/null 2>&1 && sudo wg show wg0 latest-handshakes >/dev/null 2>&1; then
  HANDSHAKE_TS=$(sudo wg show wg0 latest-handshakes | awk '{print $2}')
  CURRENT_TS=$(date +%s)
  
  if [ -n "$HANDSHAKE_TS" ] && [ "$HANDSHAKE_TS" -gt 0 ]; then
    AGE=$((CURRENT_TS - HANDSHAKE_TS))
    if [ "$AGE" -lt 180 ]; then
      echo -e "${GREEN}PASS${NC} (Last handshake ${AGE}s ago)"
    else
      echo -e "${YELLOW}WARNING${NC} (Stale handshake: ${AGE}s ago)"
    fi
  else
    echo -e "${RED}FAIL${NC} (No handshake recorded)"
    echo -e "  ${YELLOW}-> Hint: Check public keys in wg0.conf on both Node A and Node B.${NC}"
    FAILED=$((FAILED + 1))
  fi
elif command -v wg >/dev/null 2>&1 && wg show >/dev/null 2>&1; then
  if wg show | grep -q "latest handshake"; then
    echo -e "${GREEN}PASS${NC}"
  else
    echo -e "${RED}FAIL${NC} (No active handshake)"
    FAILED=$((FAILED + 1))
  fi
else
  echo -e "${YELLOW}SKIPPED${NC} (wg command requires sudo privileges)"
fi

# ------------------------------------------------------------------------------
# Check 3: HTTP Worker Health Route
# ------------------------------------------------------------------------------
echo -n "[Check 3/3] HTTP Health Probe (${HEALTH_URL})... "
RESP=$(curl -s -m 5 "$HEALTH_URL" 2>/dev/null || true)

if echo "$RESP" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  NODE_ID_FOUND=$(echo "$RESP" | grep -o '"node_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "unknown")
  echo -e "${GREEN}PASS${NC} (Response: ${RESP}, Node: ${NODE_ID_FOUND})"
else
  echo -e "${RED}FAIL${NC}"
  echo -e "  ${YELLOW}-> Received: '${RESP}'${NC}"
  echo -e "  ${YELLOW}-> Hint: Ensure ps023-worker systemd service is active on Node B and listening on ${NODE_B_IP}:${WORKER_PORT}.${NC}"
  echo -e "     Run on Node B: 'sudo systemctl status ps023-worker' and 'curl http://${NODE_B_IP}:${WORKER_PORT}/health'"
  FAILED=$((FAILED + 1))
fi

echo
echo -e "${BLUE}======================================================================${NC}"
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}ALL CHECKS PASSED: Node B is fully linked and ready for cluster scheduling!${NC}"
  exit 0
else
  echo -e "${RED}${FAILED} CHECK(S) FAILED. Resolve the errors above before launching VMs.${NC}"
  exit 1
fi
