#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000

RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"stuck","vcpus":1,"memory_mb":512,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
WID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['worker_vm_id'])")
echo "created $ID (worker id $WID)"
sleep 12

VMPID=$(pgrep -f "api-socket path=.*$WID/vm.sock" | head -n 1)
[ -n "$VMPID" ] || { echo "VMM process not found, stopping"; exit 1; }
echo ">>> freezing cloud-hypervisor pid $VMPID (SIGSTOP): it cannot answer the API"
kill -STOP "$VMPID"

echo ">>> asking the controller to stop the VM (this takes a while)"
T0=$(date +%s)
CODE=$(curl -s -o /tmp/stuck-stop.json -w '%{http_code}' -X POST -H "$API" $BASE/vms/$ID/stop)
echo "controller answered HTTP $CODE after $(( $(date +%s) - T0 ))s"
cat /tmp/stuck-stop.json; echo

echo ">>> waiting for the worker to finish its cleanup (up to 60 s more)"
for i in $(seq 1 60); do
  kill -0 "$VMPID" 2>/dev/null || { echo "process $VMPID gone after $(( $(date +%s) - T0 ))s total"; break; }
  sleep 1
done
kill -0 "$VMPID" 2>/dev/null && { echo "STILL ALIVE: leak"; kill -CONT "$VMPID"; }

echo "--- cleanup: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
