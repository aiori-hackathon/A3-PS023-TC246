#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000
export SSHPASS="$PS023_VM_PASSWORD"

RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"nestedtest","vcpus":2,"memory_mb":2048,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
IP=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['ip_address'])")
echo "created $ID at $IP"

for i in $(seq 1 40); do
  (echo > /dev/tcp/$IP/22) 2>/dev/null && break
  sleep 1
done
sleep 5

echo "--- checks run INSIDE the VM:"
sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ConnectTimeout=10 rajyavardhan@$IP \
  'hostname; uname -r; ls -l /dev/kvm 2>&1; echo "cpu flag count: $(grep -c -E "svm|vmx" /proc/cpuinfo)"; zcat /proc/config.gz 2>/dev/null | grep -E "^CONFIG_KVM(=|_AMD=|_INTEL=)" || echo "(no kernel config available)"'

echo "--- cleanup: $(curl -s -m 110 -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
