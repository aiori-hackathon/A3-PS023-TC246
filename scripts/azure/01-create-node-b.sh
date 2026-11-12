#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 1: Provision Node B Virtual Machine
# Provisions Resource Group, VNet, Subnet, NSG, Public IP, and VM.
# Target: Standard_D2s_v4 with --security-type Standard (Nested KVM)
#
# SAFETY: Dry-run by default. Requires --execute to create resources.
# IDEMPOTENCY: Safely detects existing resources and avoids conflicting recreations.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

EXECUTE=0
for arg in "$@"; do
  case "$arg" in
    --execute) EXECUTE=1 ;;
    --dry-run) EXECUTE=0 ;;
    --help|-h)
      echo "Usage: $0 [--dry-run | --execute]"
      echo "  --dry-run : Print commands and configuration without creating resources (default)"
      echo "  --execute : Provision Azure resources (REQUIRES EXPLICIT APPROVAL)"
      exit 0
      ;;
  esac
done

CALLER_IP=$(curl -s -m 5 https://api.ipify.org || curl -s -m 5 https://ifconfig.me || echo "0.0.0.0")
if [ "$CALLER_IP" != "0.0.0.0" ]; then
  CALLER_CIDR="${CALLER_IP}/32"
else
  CALLER_CIDR="*"
fi

# Zone Handling: Default is regional non-zonal deployment.
ZONE_DESC="Regional (Non-zonal deployment)"
ZONE_DRY_RUN=""
if [ -n "${AZURE_ZONE:-}" ]; then
  ZONE_DESC="Availability Zone ${AZURE_ZONE}"
  ZONE_DRY_RUN="--zone ${AZURE_ZONE} "
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE} PS-023: Provisioning Azure Node B Virtual Machine${NC}"
echo -e "${BLUE} Target Resource Group: $AZURE_RG | Region: $AZURE_LOCATION${NC}"
echo -e "${BLUE} VM SKU: $AZURE_VM_SIZE | Security Type: $AZURE_SECURITY_TYPE (Nested KVM)${NC}"
echo -e "${BLUE} Deployment Scope: $ZONE_DESC${NC}"
echo -e "${BLUE} Operator IP for Firewall: $CALLER_CIDR${NC}"
echo -e "${BLUE} SSH Key Path: $AZURE_SSH_KEY${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo

if [ "$EXECUTE" -eq 0 ]; then
  log_warn ">>> DRY-RUN MODE: Resources will NOT be created without --execute <<<"
  echo
  cat << EOF
# Azure CLI commands to be executed:
1. az group create --name $AZURE_RG --location $AZURE_LOCATION
2. az network vnet create --resource-group $AZURE_RG --name vnet-ps023 --address-prefix 10.0.0.0/16 --subnet-name snet-node-b --subnet-prefix 10.0.1.0/24
3. az network nsg create --resource-group $AZURE_RG --name nsg-ps023
4. az network nsg rule create --resource-group $AZURE_RG --nsg-name nsg-ps023 --name Allow-SSH-Caller --priority 100 --access Allow --direction Inbound --protocol Tcp --destination-port-ranges 22 --source-address-prefixes $CALLER_CIDR
5. az network nsg rule create --resource-group $AZURE_RG --nsg-name nsg-ps023 --name Allow-WireGuard-Caller --priority 200 --access Allow --direction Inbound --protocol Udp --destination-port-ranges $WG_PORT --source-address-prefixes $CALLER_CIDR
6. az network nsg rule create --resource-group $AZURE_RG --nsg-name nsg-ps023 --name Deny-Worker-API-Public --priority 1000 --access Deny --direction Inbound --protocol Tcp --destination-port-ranges $WORKER_PORT --source-address-prefixes "*"
7. az network public-ip create --resource-group $AZURE_RG --name pip-ps023-node-b --sku Standard --allocation-method Static
8. az network nic create --resource-group $AZURE_RG --name nic-ps023-node-b --vnet-name vnet-ps023 --subnet snet-node-b --network-security-group nsg-ps023 --public-ip-address pip-ps023-node-b --ip-forwarding true
9. az vm create --resource-group $AZURE_RG --name $AZURE_VM_NAME --nics nic-ps023-node-b --image $AZURE_OS_IMAGE --size $AZURE_VM_SIZE --admin-username $AZURE_ADMIN_USER --ssh-key-values @$AZURE_SSH_KEY --os-disk-size-gb $AZURE_OS_DISK_SIZE_GB --storage-sku StandardSSD_LRS --security-type $AZURE_SECURITY_TYPE ${ZONE_DRY_RUN}-o none
EOF
  echo
  if [ ! -f "$AZURE_SSH_KEY" ]; then
    log_warn "Pre-requisite check: SSH public key '$AZURE_SSH_KEY' does not yet exist."
    echo "  Generate one before executing: ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''"
    echo
  fi
  log_info "To execute, run: $0 --execute"
  exit 0
fi

# ------------------------------------------------------------------------------
# Actual Execution (Requires --execute)
# ------------------------------------------------------------------------------

# Pre-flight validation
if [ ! -f "$AZURE_SSH_KEY" ]; then
  log_err "SSH public key '$AZURE_SSH_KEY' does not exist."
  echo "Generate one before provisioning:"
  echo "  ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''"
  exit 1
fi

log_info "[1/7] Ensuring Resource Group '$AZURE_RG' in '$AZURE_LOCATION'..."
az group create --name "$AZURE_RG" --location "$AZURE_LOCATION" -o none

log_info "[2/7] Ensuring Virtual Network and Subnet..."
if az network vnet show --resource-group "$AZURE_RG" --name vnet-ps023 >/dev/null 2>&1; then
  log_info "  * Virtual Network 'vnet-ps023' already exists; reusing."
else
  az network vnet create \
    --resource-group "$AZURE_RG" \
    --name vnet-ps023 \
    --address-prefix 10.0.0.0/16 \
    --subnet-name snet-node-b \
    --subnet-prefix 10.0.1.0/24 -o none
fi

log_info "[3/7] Ensuring Network Security Group with strict firewall rules..."
if az network nsg show --resource-group "$AZURE_RG" --name nsg-ps023 >/dev/null 2>&1; then
  log_info "  * NSG 'nsg-ps023' already exists; ensuring rules."
else
  az network nsg create --resource-group "$AZURE_RG" --name nsg-ps023 -o none
fi

# NSG Rule: Allow SSH from Caller IP
if az network nsg rule show --resource-group "$AZURE_RG" --nsg-name nsg-ps023 --name Allow-SSH-Caller >/dev/null 2>&1; then
  az network nsg rule update \
    --resource-group "$AZURE_RG" \
    --nsg-name nsg-ps023 \
    --name Allow-SSH-Caller \
    --source-address-prefixes "$CALLER_CIDR" -o none
else
  az network nsg rule create \
    --resource-group "$AZURE_RG" \
    --nsg-name nsg-ps023 \
    --name Allow-SSH-Caller \
    --priority 100 \
    --access Allow \
    --direction Inbound \
    --protocol Tcp \
    --destination-port-ranges 22 \
    --source-address-prefixes "$CALLER_CIDR" -o none
fi

# NSG Rule: Allow WireGuard UDP from Caller IP
if az network nsg rule show --resource-group "$AZURE_RG" --nsg-name nsg-ps023 --name Allow-WireGuard-Caller >/dev/null 2>&1; then
  az network nsg rule update \
    --resource-group "$AZURE_RG" \
    --nsg-name nsg-ps023 \
    --name Allow-WireGuard-Caller \
    --source-address-prefixes "$CALLER_CIDR" -o none
else
  az network nsg rule create \
    --resource-group "$AZURE_RG" \
    --nsg-name nsg-ps023 \
    --name Allow-WireGuard-Caller \
    --priority 200 \
    --access Allow \
    --direction Inbound \
    --protocol Udp \
    --destination-port-ranges "$WG_PORT" \
    --source-address-prefixes "$CALLER_CIDR" -o none
fi

# NSG Rule: Explicit Deny on public port 8002
if az network nsg rule show --resource-group "$AZURE_RG" --nsg-name nsg-ps023 --name Deny-Worker-API-Public >/dev/null 2>&1; then
  log_info "  * Rule 'Deny-Worker-API-Public' already exists."
else
  az network nsg rule create \
    --resource-group "$AZURE_RG" \
    --nsg-name nsg-ps023 \
    --name Deny-Worker-API-Public \
    --priority 1000 \
    --access Deny \
    --direction Inbound \
    --protocol Tcp \
    --destination-port-ranges "$WORKER_PORT" \
    --source-address-prefixes "*" -o none
fi

log_info "[4/7] Ensuring Static Public IP..."
if az network public-ip show --resource-group "$AZURE_RG" --name pip-ps023-node-b >/dev/null 2>&1; then
  log_info "  * Public IP 'pip-ps023-node-b' already exists; reusing."
else
  az network public-ip create \
    --resource-group "$AZURE_RG" \
    --name pip-ps023-node-b \
    --sku Standard \
    --allocation-method Static -o none
fi

log_info "[5/7] Ensuring Network Interface with IP forwarding enabled..."
if az network nic show --resource-group "$AZURE_RG" --name nic-ps023-node-b >/dev/null 2>&1; then
  log_info "  * NIC 'nic-ps023-node-b' already exists; reusing."
else
  az network nic create \
    --resource-group "$AZURE_RG" \
    --name nic-ps023-node-b \
    --vnet-name vnet-ps023 \
    --subnet snet-node-b \
    --network-security-group nsg-ps023 \
    --public-ip-address pip-ps023-node-b \
    --ip-forwarding true -o none
fi

log_info "[6/7] Deploying Virtual Machine '$AZURE_VM_NAME' (--security-type $AZURE_SECURITY_TYPE, $ZONE_DESC)..."
if az vm show --resource-group "$AZURE_RG" --name "$AZURE_VM_NAME" >/dev/null 2>&1; then
  log_ok "Virtual Machine '$AZURE_VM_NAME' already exists in '$AZURE_RG'."
else
  VM_CMD=(
    az vm create
    --resource-group "$AZURE_RG"
    --name "$AZURE_VM_NAME"
    --nics nic-ps023-node-b
    --image "$AZURE_OS_IMAGE"
    --size "$AZURE_VM_SIZE"
    --admin-username "$AZURE_ADMIN_USER"
    --ssh-key-values @"$AZURE_SSH_KEY"
    --os-disk-size-gb "$AZURE_OS_DISK_SIZE_GB"
    --storage-sku StandardSSD_LRS
    --security-type "$AZURE_SECURITY_TYPE"
  )
  if [ -n "${AZURE_ZONE:-}" ]; then
    VM_CMD+=(--zone "$AZURE_ZONE")
  fi
  VM_CMD+=(-o none)

  "${VM_CMD[@]}"
fi

log_info "[7/7] Retrieving assigned Public IP..."
PUBLIC_IP=$(az network public-ip show --resource-group "$AZURE_RG" --name pip-ps023-node-b --query ipAddress -o tsv)

ENV_FILE="$SCRIPT_DIR/node_b.env"
cat > "$ENV_FILE" << EOF
AZURE_NODE_B_PUBLIC_IP=$PUBLIC_IP
AZURE_NODE_B_ADMIN_USER=$AZURE_ADMIN_USER
AZURE_NODE_B_RG=$AZURE_RG
AZURE_NODE_B_VM_NAME=$AZURE_VM_NAME
EOF
chmod 600 "$ENV_FILE"

log_ok "VM Successfully Deployed!"
echo "Assigned Public IP: $PUBLIC_IP"
echo "Saved environment to: $ENV_FILE"
echo "Proceed to 02-bootstrap-node-b.sh to configure KVM, networking, and dependencies."
