#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000

RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"vmmcrash","vcpus":1,"memory_mb":512,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
NODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")
WID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['worker_vm_id'])")
echo "created $ID on $NODE (worker id $WID)"
sleep 12

VMPID=$(pgrep -f "api-socket path=.*$WID/vm.sock" | head -n 1)
[ -n "$VMPID" ] || { echo "VMM process not found, stopping"; exit 1; }
echo ">>> SIGKILL on cloud-hypervisor pid $VMPID"
kill -9 "$VMPID"

for i in $(seq 1 8); do
  S=$(curl -s -H "$API" $BASE/vms/$ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
  echo "$(date +%T) controller says: $S   vmm-processes=$(pgrep -fc cloud-hypervisor)"
  sleep 5
done

echo "--- worker folders left:"; ls ~/ps023/vms/ ~/ps023/vms-b/
echo "--- restart the VM through the controller:"
curl -s -X POST -H "$API" $BASE/vms/$ID/start | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status'), d.get('detail'))"
sleep 12
echo "--- cleanup: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
