#!/usr/bin/env bash
# ==============================================================================
# PS-023: Microsoft Azure VM Provisioning Script (Node B)
# Target: Standard_D2s_v4 (2 vCPU, 8 GiB RAM, Nested KVM)
# OS: Ubuntu 24.04 LTS (Canonical:ubuntu-24_04-lts:server:latest)
#
# SAFETY NOTICE:
# This script will NOT create any cloud resources without explicit confirmation.
# Use --dry-run to inspect generated commands.
# ==============================================================================
set -euo pipefail

# Configuration defaults
RESOURCE_GROUP="${AZURE_RG:-rg-ps023}"
LOCATION="${AZURE_LOCATION:-centralindia}"          # Central India (Pune) first
LOCATION_FALLBACK="southeastasia"                   # Southeast Asia (Singapore) fallback
VM_NAME="${AZURE_VM_NAME:-ps023-node-b}"
VM_SIZE="${AZURE_VM_SIZE:-Standard_D2s_v4}"
OS_IMAGE="Canonical:ubuntu-24_04-lts:server:latest"
ADMIN_USER="${AZURE_ADMIN_USER:-ubuntu}"
SSH_KEY_PATH="${AZURE_SSH_KEY:-$HOME/.ssh/id_rsa.pub}"
OS_DISK_SIZE_GB=30

DRY_RUN=1
for arg in "$@"; do
  case "$arg" in
    --execute)
      DRY_RUN=0
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    --help|-h)
      echo "Usage: $0 [--dry-run | --execute]"
      echo "  --dry-run: Print planned commands and cost estimate without creating resources (default)"
      echo "  --execute: Execute Azure resource creation (REQUIRES EXPLICIT APPROVAL)"
      exit 0
      ;;
  esac
done

# Detect caller's public IP for strict firewall rules
CALLER_IP=$(curl -s -m 5 https://api.ipify.org || curl -s -m 5 https://ifconfig.me || echo "MY_IP")

echo "======================================================================"
echo " PS-023: Azure Node B VM Provisioning Planner"
echo "======================================================================"
echo "Target Resource Group: $RESOURCE_GROUP"
echo "Target Region:         $LOCATION (Fallback: $LOCATION_FALLBACK)"
echo "Target VM Name:        $VM_NAME"
echo "VM Size:               $VM_SIZE (2 vCPUs, 8 GiB RAM, Nested KVM)"
echo "OS Image:              $OS_IMAGE"
echo "Admin User:            $ADMIN_USER"
echo "SSH Public Key:        $SSH_KEY_PATH"
echo "OS Disk:               ${OS_DISK_SIZE_GB} GiB Standard SSD (gp3 equivalent)"
echo "Caller Public IP:      $CALLER_IP/32"
echo "======================================================================"
echo

echo "ESTIMATED COSTS & PRICING:"
echo "----------------------------------------------------------------------"
echo "1. VM Compute (Standard_D2s_v4):"
echo "   - Central India: ~\$0.096/hour (~INR 8.1/hour)"
echo "   - Southeast Asia: ~\$0.104/hour (~INR 8.8/hour)"
echo "   - 10 hours of active testing: ~\$0.96 - \$1.04"
echo "2. Storage (30 GiB Standard SSD / Managed Disk):"
echo "   - ~\$2.40/month (~\$0.08/day)"
echo "3. Standard Public IPv4 (Static):"
echo "   - ~\$0.005/hour (~\$0.12/day)"
echo "4. Inbound / Internal Data Transfer:"
echo "   - Free. Outbound data transfer first 100 GB/month free on Azure."
echo "5. Total estimated cost for a 1-day evaluation (8h running, 16h stopped):"
echo "   - ~\$0.77 - \$0.89 total compute + ~\$0.12 public IP + storage (Static unverified estimate)."
echo "----------------------------------------------------------------------"
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo ">>> DRY-RUN MODE: Printing Azure CLI deployment commands without execution <<<"
  echo
  cat << EOF
# 1. Ensure Azure CLI is authenticated:
az login
az account show

# 2. Check VM Family Quota in the selected region:
az vm list-usage --location $LOCATION --query "[?contains(name.value, 'StandardDSv5Family')]" -o table

# 3. Create Resource Group:
az group create \\
  --name $RESOURCE_GROUP \\
  --location $LOCATION

# 4. Create Virtual Network & Subnet:
az network vnet create \\
  --resource-group $RESOURCE_GROUP \\
  --name vnet-ps023 \\
  --address-prefix 10.0.0.0/16 \\
  --subnet-name snet-node-b \\
  --subnet-prefix 10.0.1.0/24

# 5. Create Network Security Group (NSG) with strict firewall rules:
az network nsg create \\
  --resource-group $RESOURCE_GROUP \\
  --name nsg-ps023-node-b

# Rule A: Allow SSH from trusted IP only (port 22)
az network nsg rule create \\
  --resource-group $RESOURCE_GROUP \\
  --nsg-name nsg-ps023-node-b \\
  --name Allow-SSH-Caller \\
  --priority 1000 \\
  --direction Inbound \\
  --access Allow \\
  --protocol Tcp \\
  --source-address-prefixes "${CALLER_IP}/32" \\
  --source-port-ranges "*" \\
  --destination-port-ranges 22

# Rule B: Allow WireGuard UDP (port 51820)
az network nsg rule create \\
  --resource-group $RESOURCE_GROUP \\
  --nsg-name nsg-ps023-node-b \\
  --name Allow-WireGuard-UDP \\
  --priority 1010 \\
  --direction Inbound \\
  --access Allow \\
  --protocol Udp \\
  --source-address-prefixes "${CALLER_IP}/32" \\
  --source-port-ranges "*" \\
  --destination-port-ranges 51820

# Rule C: Explicitly Deny Public Worker API (port 8002) from Internet
# (Worker must only be accessed over private WireGuard tunnel: 10.100.0.2:8002)
az network nsg rule create \\
  --resource-group $RESOURCE_GROUP \\
  --nsg-name nsg-ps023-node-b \\
  --name Deny-Worker-API-Public \\
  --priority 1020 \\
  --direction Inbound \\
  --access Deny \\
  --protocol Tcp \\
  --source-address-prefixes "Internet" \\
  --source-port-ranges "*" \\
  --destination-port-ranges 8002

# 6. Allocate Static Public IP:
az network public-ip create \\
  --resource-group $RESOURCE_GROUP \\
  --name pip-ps023-node-b \\
  --sku Standard \\
  --allocation-method Static

# 7. Create Network Interface (NIC):
az network nic create \\
  --resource-group $RESOURCE_GROUP \\
  --name nic-ps023-node-b \\
  --vnet-name vnet-ps023 \\
  --subnet snet-node-b \\
  --network-security-group nsg-ps023-node-b \\
  --public-ip-address pip-ps023-node-b

# 8. Create Virtual Machine (CRITICAL: --security-type Standard for nested KVM):
az vm create \\
  --resource-group $RESOURCE_GROUP \\
  --name $VM_NAME \\
  --nics nic-ps023-node-b \\
  --image "$OS_IMAGE" \\
  --size "$VM_SIZE" \\
  --admin-username "$ADMIN_USER" \\
  --ssh-key-values "$SSH_KEY_PATH" \\
  --os-disk-size-gb $OS_DISK_SIZE_GB \\
  --storage-sku StandardSSD_LRS \\
  --security-type Standard

# 9. Get Node B Public IP:
az network public-ip show \\
  --resource-group $RESOURCE_GROUP \\
  --name pip-ps023-node-b \\
  --query ipAddress -o tsv
EOF
  echo
  echo "Dry run complete. No cloud resources were created or modified."
  echo "To execute these commands, ensure Azure CLI is logged in and run with: --execute"
  exit 0
fi

# Execution branch (Requires explicit user confirmation)
echo "WARNING: Executing this script will create Azure resources and incur charges against your account."
echo "Press Ctrl+C to abort now, or enter 'CONFIRM_AZURE_DEPLOY' to proceed:"
read -r CONFIRMATION
if [ "$CONFIRMATION" != "CONFIRM_AZURE_DEPLOY" ]; then
  echo "Aborted by user safety check."
  exit 1
fi

command -v az >/dev/null 2>&1 || {
  echo "ERROR: Azure CLI (az) is not installed on this machine." >&2
  echo "Please install Azure CLI or execute the dry-run commands above via the Azure Cloud Shell." >&2
  exit 1
}

echo "Checking active Azure subscription..."
az account show --output table

echo "Proceeding with Azure deployment..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
az network vnet create --resource-group "$RESOURCE_GROUP" --name vnet-ps023 --address-prefix 10.0.0.0/16 --subnet-name snet-node-b --subnet-prefix 10.0.1.0/24
az network nsg create --resource-group "$RESOURCE_GROUP" --name nsg-ps023-node-b
az network nsg rule create --resource-group "$RESOURCE_GROUP" --nsg-name nsg-ps023-node-b --name Allow-SSH-Caller --priority 1000 --direction Inbound --access Allow --protocol Tcp --source-address-prefixes "${CALLER_IP}/32" --destination-port-ranges 22
az network nsg rule create --resource-group "$RESOURCE_GROUP" --nsg-name nsg-ps023-node-b --name Allow-WireGuard-UDP --priority 1010 --direction Inbound --access Allow --protocol Udp --source-address-prefixes "${CALLER_IP}/32" --destination-port-ranges 51820
az network nsg rule create --resource-group "$RESOURCE_GROUP" --nsg-name nsg-ps023-node-b --name Deny-Worker-API-Public --priority 1020 --direction Inbound --access Deny --protocol Tcp --source-address-prefixes "Internet" --destination-port-ranges 8002
az network public-ip create --resource-group "$RESOURCE_GROUP" --name pip-ps023-node-b --sku Standard --allocation-method Static
az network nic create --resource-group "$RESOURCE_GROUP" --name nic-ps023-node-b --vnet-name vnet-ps023 --subnet snet-node-b --network-security-group nsg-ps023-node-b --public-ip-address pip-ps023-node-b
az vm create --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --nics nic-ps023-node-b --image "$OS_IMAGE" --size "$VM_SIZE" --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_KEY_PATH" --os-disk-size-gb "$OS_DISK_SIZE_GB" --storage-sku StandardSSD_LRS --security-type Standard

NODE_B_PUB_IP=$(az network public-ip show --resource-group "$RESOURCE_GROUP" --name pip-ps023-node-b --query ipAddress -o tsv)
echo "VM successfully provisioned! Public IP: $NODE_B_PUB_IP"
