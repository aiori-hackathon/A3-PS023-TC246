#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration Common Configuration & Helper Functions
# ==============================================================================
set -euo pipefail

# Azure Infrastructure Defaults
export AZURE_RG="${AZURE_RG:-rg-ps023}"
export AZURE_LOCATION="${AZURE_LOCATION:-centralindia}"          # Primary: Pune, India
export AZURE_LOCATION_FALLBACK="${AZURE_LOCATION_FALLBACK:-southeastasia}" # Fallback: Singapore
export AZURE_VM_NAME="${AZURE_VM_NAME:-ps023-node-b}"
export AZURE_VM_SIZE="${AZURE_VM_SIZE:-Standard_D2s_v4}"          # 2 vCPU, 8 GiB RAM, Nested KVM (standardDSv4Family)
export AZURE_SECURITY_TYPE="${AZURE_SECURITY_TYPE:-Standard}"    # Standard security required for nested KVM
export AZURE_ZONE="${AZURE_ZONE:-}"                              # Empty = regional non-zonal deployment (default)
export AZURE_OS_IMAGE="${AZURE_OS_IMAGE:-Canonical:ubuntu-24_04-lts:server:latest}"
export AZURE_ADMIN_USER="${AZURE_ADMIN_USER:-ubuntu}"
export AZURE_SSH_KEY="${AZURE_SSH_KEY:-$HOME/.ssh/id_rsa.pub}"
export AZURE_OS_DISK_SIZE_GB=30

# Network Defaults
export WG_INTERFACE="${WG_INTERFACE:-wg0}"
export WG_NODE_A_IP="10.100.0.1"
export WG_NODE_B_IP="10.100.0.2"
export WG_PORT=51820
export WORKER_PORT=8002

# Color Output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }
