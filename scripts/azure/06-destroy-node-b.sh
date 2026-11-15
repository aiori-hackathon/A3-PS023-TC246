#!/usr/bin/env bash
# ==============================================================================
# PS-023: Azure Migration — Step 6: Cost Control, Deallocation & Cleanup
# Safely deallocates VM (compute billing = $0.00/hr) or tears down resources.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

ACTION="${1:---help}"

case "$ACTION" in
  --stop|--deallocate)
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "${BLUE} Deallocating Azure Node B VM: $AZURE_VM_NAME${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo "Note: Deallocated VMs incur NO compute charges (\$0.00/hour)."
    echo "Disk charges persist (~30 GiB Standard SSD ≈ \$0.08/day)."
    echo
    if command -v az >/dev/null 2>&1; then
      az vm deallocate --resource-group "$AZURE_RG" --name "$AZURE_VM_NAME"
      log_ok "VM '$AZURE_VM_NAME' deallocated successfully."
      echo "To power it back on later: az vm start --resource-group $AZURE_RG --name $AZURE_VM_NAME"
    else
      echo "Run manually:"
      echo "  az vm deallocate --resource-group $AZURE_RG --name $AZURE_VM_NAME"
    fi
    ;;

  --delete|--destroy)
    echo -e "${RED}======================================================================${NC}"
    echo -e "${RED} CAUTION: PERMANENT DESTRUCTION OF AZURE RESOURCE GROUP '$AZURE_RG'${NC}"
    echo -e "${RED} This will delete the VM, disk, IP, NSG, and all cloud data!${NC}"
    echo -e "${RED}======================================================================${NC}"
    read -r -p "Are you sure you want to permanently delete Resource Group '$AZURE_RG'? Type 'yes': " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
      echo "Destruction cancelled."
      exit 0
    fi
    if command -v az >/dev/null 2>&1; then
      log_warn "Deleting Resource Group '$AZURE_RG'..."
      az group delete --name "$AZURE_RG" --yes --no-wait
      rm -f "$SCRIPT_DIR/node_b.env"
      log_ok "Deletion initiated in background. Billing will terminate once cleanup completes."
    else
      echo "Run manually:"
      echo "  az group delete --name $AZURE_RG --yes"
    fi
    ;;

  --help|-h|*)
    echo "Usage: $0 [--deallocate | --destroy]"
    echo
    echo "  --deallocate : Stop the Azure VM to freeze compute billing (\$0/hr, recommended)"
    echo "  --destroy    : Permanently delete Resource Group '$AZURE_RG' and all resources"
    exit 0
    ;;
esac
