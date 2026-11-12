#!/usr/bin/env bash
# ==============================================================================
# PS-023: Microsoft Azure Resource Cleanup and Cost-Control Script
# Provides options to stop (deallocate compute to stop billing) or completely
# delete Azure resources created for Node B.
# ==============================================================================
set -euo pipefail

RESOURCE_GROUP="${AZURE_RG:-rg-ps023}"
VM_NAME="${AZURE_VM_NAME:-ps023-node-b}"

ACTION="${1:-help}"

case "$ACTION" in
  stop|deallocate)
    echo "======================================================================"
    echo "Deallocating VM '$VM_NAME' in Resource Group '$RESOURCE_GROUP'..."
    echo "NOTE: Deallocated VMs incur NO compute charges ($0.00/hour)."
    echo "Only minimal storage charges apply (30 GiB Standard SSD ≈ $2.40/month)."
    echo "======================================================================"
    echo "Run the following command:"
    echo "  az vm deallocate --resource-group $RESOURCE_GROUP --name $VM_NAME"
    echo
    echo "To start the VM again later:"
    echo "  az vm start --resource-group $RESOURCE_GROUP --name $VM_NAME"
    ;;
  
  delete|destroy)
    echo "======================================================================"
    echo "WARNING: DESTRUCTIVE ACTION - COMPLETE RESOURCE GROUP DELETION"
    echo "This will permanently delete Resource Group '$RESOURCE_GROUP' and ALL"
    echo "associated resources (VM, disks, NIC, NSG, VNet, Public IP)."
    echo "======================================================================"
    echo "To completely tear down all Azure resources:"
    echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
    ;;

  *)
    echo "Usage: $0 [stop | delete]"
    echo
    echo "  stop   : Deallocate the Azure VM to freeze compute billing (recommended when paused)"
    echo "  delete : Permanently remove all Azure resources and terminate billing"
    exit 0
    ;;
esac
