#!/bin/bash
set -euo pipefail

P=$HOME/ps023
SECRETS=$P/secrets.env
[ -f "$SECRETS" ] && . "$SECRETS"

AZURE_RG="${AZURE_RG:-rg-ps023}"
AZURE_VM="${AZURE_VM:-ps023-node-b}"

echo "=== Azure Node B Teardown ==="

# 1. Delete test VMs on Node B via controller API
if [ -n "${PS023_API_TOKEN:-}" ]; then
  echo "Checking for running VMs via controller API..."
  VMS=$(curl -s -m 3 -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/vms 2>/dev/null || true)
  if [ -n "$VMS" ] && echo "$VMS" | grep -q '"id"'; then
    VM_IDS=$(echo "$VMS" | python3 -c 'import sys, json
try:
    data = json.load(sys.stdin)
    for vm in data:
        if vm.get("node_id") == "node-b":
            print(vm.get("id"))
except Exception:
    pass')
    for vm_id in $VM_IDS; do
      echo "Deleting VM $vm_id on Node B..."
      curl -s -m 10 -X DELETE -H "Authorization: Bearer $PS023_API_TOKEN" "http://127.0.0.1:8000/vms/$vm_id" || true
    done
  fi
fi

# 2. Stop SSH tunnel and sshuttle
echo "Stopping SSH tunnel and sshuttle..."
pkill -f '8012:127.0.0.1:8002' 2>/dev/null || true
pkill -f 'sshuttle' 2>/dev/null || true
sudo -n pkill -f 'sshuttle' 2>/dev/null || true

# 3. Take down WireGuard if used
if ip link show wg0 >/dev/null 2>&1; then
  echo "Taking down WireGuard wg0 interface..."
  sudo -n wg-quick down wg0 2>/dev/null || true
fi

# 4. Deallocate Azure VM
echo "Deallocating Azure VM '$AZURE_VM' in resource group '$AZURE_RG'..."
az vm deallocate --resource-group "$AZURE_RG" --name "$AZURE_VM" --no-wait

# 5. Confirm "VM deallocated"
echo "Waiting for '$AZURE_VM' to enter 'VM deallocated'..."
while true; do
  STATUS=$(az vm get-instance-view -g "$AZURE_RG" -n "$AZURE_VM" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv 2>/dev/null || true)
  echo "Power status: $STATUS"
  if [ "$STATUS" = "VM deallocated" ]; then
    break
  fi
  sleep 5
done

echo "SUCCESS: Azure VM '$AZURE_VM' deallocated. Teardown complete."
