#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000
RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"nestedtest","vcpus":2,"memory_mb":2048,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
IP=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['ip_address'])")
echo "$ID" > /tmp/nested-test.id
echo "created $ID at $IP (id saved in /tmp/nested-test.id)"
echo "waiting 20 s for boot..."
sleep 20
echo "now run:  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null rajyavardhan@$IP"
