#!/usr/bin/env bash
# ==============================================================================
# PS-023: Microsoft Azure Node B Deployment & Link Verification Script
# Runs from Node A (Laptop Controller) to verify WireGuard tunnel, handshake,
# and authenticated Worker HTTP API on Azure Node B.
# ==============================================================================
set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

FAILED=0
NODE_B_IP="${PS023_NODE_B_IP:-10.100.0.2}"
WORKER_PORT="${PS023_WORKER_PORT:-8002}"
HEALTH_URL="http://${NODE_B_IP}:${WORKER_PORT}/health"
RESOURCES_URL="http://${NODE_B_IP}:${WORKER_PORT}/resources"
TOKEN="${PS023_TOKEN_NODE_B:-}"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE} PS-023: Azure Hybrid Deployment Verification (Node A -> Azure Node B)${NC}"
echo -e "${BLUE} Target Worker Endpoint: ${HEALTH_URL}${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo

# ------------------------------------------------------------------------------
# Check 1: Local WireGuard Interface
# ------------------------------------------------------------------------------
echo -n "[Check 1/5] Local WireGuard wg0 Interface... "
if ip link show wg0 >/dev/null 2>&1; then
  WG_ADDR=$(ip -4 addr show wg0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "unknown")
  echo -e "${GREEN}PASS${NC} (Active, IP: ${WG_ADDR})"
else
  echo -e "${RED}FAIL${NC}"
  echo -e "  ${YELLOW}-> wg0 is not active on this machine.${NC}"
  echo -e "     Run: 'sudo wg-quick up wg0' after configuring /etc/wireguard/wg0.conf."
  FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# Check 2: ICMP Ping to Node B WireGuard IP (10.100.0.2)
# ------------------------------------------------------------------------------
echo -n "[Check 2/5] ICMP Ping to Node B (${NODE_B_IP})... "
if ping -c 3 -W 2 "$NODE_B_IP" >/dev/null 2>&1; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL${NC}"
  echo -e "  ${YELLOW}-> Ping failed to ${NODE_B_IP}.${NC}"
  echo -e "     Check that Azure NSG permits UDP 51820 from your public IP,"
  echo -e "     and that wg-quick@wg0 is running on the Azure VM."
  FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# Check 3: WireGuard Handshake Verification
# ------------------------------------------------------------------------------
echo -n "[Check 3/5] WireGuard Handshake... "
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
    echo -e "  ${YELLOW}-> Check public keys in wg0.conf on both sides.${NC}"
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
# Check 4: Unauthenticated Worker Health Probe (/health)
# ------------------------------------------------------------------------------
echo -n "[Check 4/5] Worker HTTP Health Probe (${HEALTH_URL})... "
RESP=$(curl -s -m 5 "$HEALTH_URL" 2>/dev/null || true)

if echo "$RESP" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  NODE_ID_FOUND=$(echo "$RESP" | grep -o '"node_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "unknown")
  echo -e "${GREEN}PASS${NC} (Node ID: ${CYAN}${NODE_ID_FOUND}${NC})"
else
  echo -e "${RED}FAIL${NC}"
  echo -e "  ${YELLOW}-> Received: '${RESP}'${NC}"
  echo -e "  ${YELLOW}-> Hint: Verify ps023-worker service is running on Azure VM and listening on ${NODE_B_IP}:${WORKER_PORT}.${NC}"
  FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# Check 5: Authenticated Worker Resources Probe (/resources)
# ------------------------------------------------------------------------------
echo -n "[Check 5/5] Worker Authenticated Resources Probe (/resources)... "
if [ -n "$TOKEN" ]; then
  AUTH_RESP=$(curl -s -m 5 -H "Authorization: Bearer $TOKEN" "$RESOURCES_URL" 2>/dev/null || true)
  if echo "$AUTH_RESP" | grep -q "memory_schedulable_mb"; then
    MEM_SCHED=$(echo "$AUTH_RESP" | grep -o '"memory_schedulable_mb"[[:space:]]*:[[:space:]]*[0-9]*' | awk -F: '{print $2}' | tr -d ' ')
    KVM_CGROUPS=$(echo "$AUTH_RESP" | grep -o '"cgroups_enabled"[[:space:]]*:[[:space:]]*[a-zA-Z]*' || true)
    echo -e "${GREEN}PASS${NC} (Schedulable Memory: ${MEM_SCHED} MB, ${KVM_CGROUPS})"
  else
    echo -e "${RED}FAIL${NC} (Response: ${AUTH_RESP})"
    FAILED=$((FAILED + 1))
  fi
else
  echo -e "${YELLOW}SKIPPED${NC} (PS023_TOKEN_NODE_B not set in environment)"
fi

echo
echo -e "${BLUE}======================================================================${NC}"
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}ALL CHECKS PASSED: Azure Node B is fully operational and reachable!${NC}"
  echo -e "Controller can now schedule VMs to Azure Node B using: PS023_NODES=node-a=http://127.0.0.1:8001,node-b=http://${NODE_B_IP}:${WORKER_PORT}"
  exit 0
else
  echo -e "${RED}${FAILED} CHECK(S) FAILED. Please review the hints above.${NC}"
  exit 1
fi
