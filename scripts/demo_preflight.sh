#!/usr/bin/env bash
# ==============================================================================
# PS-023: Live Demonstration Pre-Flight Sanity Checker (Read-Only)
# ==============================================================================
# Verifies host health, resource headroom, clean port/process state,
# dashboard build, database integrity, and nested Node B prerequisites.
# ==============================================================================

set -uo pipefail

FAILED=0
WARNED=0

pass() {
    printf "[ \033[32mPASS\033[0m ] %s\n" "$1"
}

warn() {
    printf "[ \033[33mWARN\033[0m ] %s\n" "$1"
    WARNED=$((WARNED + 1))
}

fail() {
    printf "[ \033[31mFAIL\033[0m ] %s\n" "$1"
    FAILED=$((FAILED + 1))
}

echo "================================================================================"
echo "PS-023: Live Demonstration Pre-Flight Sanity Check"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "================================================================================"

# 1. RAM & Swap Check
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
AVAIL_RAM=$(free -m | awk '/^Mem:/{print $7}')
USED_SWAP=$(free -m | awk '/^Swap:/{print $3}')
TOTAL_SWAP=$(free -m | awk '/^Swap:/{print $2}')

if [ "$AVAIL_RAM" -lt 1500 ]; then
    fail "Host available RAM is critically low: ${AVAIL_RAM} MB (minimum required: 1500 MB)"
elif [ "$AVAIL_RAM" -lt 3000 ]; then
    warn "Host available RAM is tight: ${AVAIL_RAM} MB available (total: ${TOTAL_RAM} MB)"
else
    pass "Host memory sufficient: ${AVAIL_RAM} MB available / ${TOTAL_RAM} MB total"
fi

if [ "$USED_SWAP" -gt 4096 ]; then
    warn "Host swap usage is high: ${USED_SWAP} MB / ${TOTAL_SWAP} MB (consider closing heavy apps)"
else
    pass "Swap usage normal: ${USED_SWAP} MB used / ${TOTAL_SWAP} MB total"
fi

# 2. Available RAM vs HOST_RESERVE_MB (1024 MB)
HOST_RESERVE_MB=1024
if [ "$AVAIL_RAM" -gt "$HOST_RESERVE_MB" ]; then
    SCHED_MB=$((AVAIL_RAM - HOST_RESERVE_MB))
else
    SCHED_MB=0
fi

echo "--------------------------------------------------------------------------------"
echo "node A schedulable memory will be about ${SCHED_MB} MB"
echo "--------------------------------------------------------------------------------"

if [ "$SCHED_MB" -lt 512 ]; then
    fail "Node A schedulable memory (${SCHED_MB} MB) is below 512 MB minimum"
elif [ "$SCHED_MB" -lt 1500 ]; then
    warn "Node A schedulable memory (${SCHED_MB} MB) is below 1500 MB headroom guideline"
else
    pass "Node A schedulable headroom healthy: ${SCHED_MB} MB (reserve: ${HOST_RESERVE_MB} MB)"
fi

# 3. Check for stale cloud-hypervisor processes
CH_PROCS=$(pgrep -x cloud-hypervisor 2>/dev/null || true)
if [ -n "$CH_PROCS" ]; then
    fail "Stale cloud-hypervisor process(es) detected (PID(s): $(echo $CH_PROCS | tr '\n' ' '))"
else
    pass "Zero stale cloud-hypervisor processes running"
fi

# 4. Check for leftover ps023-vmm cgroups
CGROUP_LEFTOVERS=$(find /sys/fs/cgroup -maxdepth 5 -type d -name "ps023-vmm*" 2>/dev/null || true)
if [ -n "$CGROUP_LEFTOVERS" ]; then
    fail "Leftover ps023-vmm cgroups detected under /sys/fs/cgroup"
else
    pass "Zero leftover ps023-vmm cgroup slices present"
fi

# 5. Check ports 8000, 8001, 8002, 3000 are free
OCCUPIED_PORTS=$(ss -tulpn | grep -E ':(8000|8001|8002|3000)\b' || true)
if [ -n "$OCCUPIED_PORTS" ]; then
    fail "Pre-bringup port conflict detected on 8000/8001/8002/3000:"
    echo "$OCCUPIED_PORTS"
else
    pass "All required ports free (8000, 8001, 8002, 3000)"
fi

# 6. Check br-ps023 bridge state
if ip link show br-ps023 &>/dev/null; then
    BR_STATE=$(ip -br link show br-ps023 | awk '{print $2}')
    pass "Bridge br-ps023 exists on host (state: ${BR_STATE})"
else
    warn "Bridge br-ps023 not yet created (bring-up.sh will create it via sudo)"
fi

# 7. Check Dashboard Assets
DASHBOARD_HTML="/home/rajyavardhan/ps023/controller/dashboard/index.html"
DASHBOARD_ASSETS="/home/rajyavardhan/ps023/controller/dashboard/assets"
if [ -f "$DASHBOARD_HTML" ] && [ -d "$DASHBOARD_ASSETS" ] && [ "$(ls -A "$DASHBOARD_ASSETS" 2>/dev/null)" ]; then
    pass "Dashboard SPA assets verified at controller/dashboard/"
else
    fail "Dashboard SPA assets missing or incomplete (run 'npm run build' in frontend/)"
fi

# 8. Check Controller DB for placeholder images
DB_PATH="/home/rajyavardhan/ps023/controller.db"
if [ -f "$DB_PATH" ]; then
    PLACEHOLDER_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM images WHERE id LIKE '%placeholder%' OR path LIKE '%placeholder%';" 2>/dev/null || echo "0")
    if [ "$PLACEHOLDER_COUNT" -gt 0 ]; then
        fail "Controller DB contains ${PLACEHOLDER_COUNT} placeholder image row(s)"
    else
        pass "Controller DB image catalog clean (0 placeholder rows)"
    fi
else
    warn "Controller DB file not present yet at ${DB_PATH} (will be created on first start)"
fi

# 9. Check API Token is Loaded (Never print token)
if [ -n "${PS023_API_TOKEN:-}" ]; then
    pass "PS023_API_TOKEN is actively exported in environment"
elif [ -f "/home/rajyavardhan/ps023/secrets.env" ] && grep -q '^PS023_API_TOKEN=' "/home/rajyavardhan/ps023/secrets.env"; then
    pass "PS023_API_TOKEN present in secrets.env (remember to invoke with with-secrets.sh)"
else
    fail "PS023_API_TOKEN is missing from environment and secrets.env"
fi

# 10. Check Node B Nested Disk Image
NESTED_DISK="/home/rajyavardhan/ps023/outer/disk.raw"
if [ -f "$NESTED_DISK" ]; then
    DISK_SIZE=$(ls -lh "$NESTED_DISK" | awk '{print $5}')
    pass "Nested Node B disk image exists: ${NESTED_DISK} (${DISK_SIZE})"
else
    fail "Nested Node B disk image missing at ${NESTED_DISK}"
fi

echo "================================================================================"
if [ "$FAILED" -eq 0 ]; then
    echo -e "\033[32mPRE-FLIGHT RESULT: SUCCESS\033[0m (0 failures, ${WARNED} warnings)"
    echo "Cluster host is clean and ready for bring-up."
    exit 0
else
    echo -e "\033[31mPRE-FLIGHT RESULT: FAILED\033[0m (${FAILED} failure(s), ${WARNED} warnings)"
    echo "Please resolve the above failures before running bring-up.sh."
    exit 1
fi
