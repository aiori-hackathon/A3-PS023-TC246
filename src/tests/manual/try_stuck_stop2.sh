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
echo ">>> freezing pid $VMPID (SIGSTOP)"
kill -STOP "$VMPID"

T0=$(date +%s)
curl -s -o /tmp/stuck-stop.json -w ">>> controller answered HTTP %{http_code}\n" \
  -X POST -H "$API" $BASE/vms/$ID/stop &

for i in $(seq 1 32); do
  ST=$(ps -o stat= -p "$VMPID" 2>/dev/null)
  echo "t=$(( $(date +%s) - T0 ))s  process state=[${ST:-gone}]"
  [ -z "$ST" ] && break
  sleep 5
done
wait

if ps -p "$VMPID" > /dev/null 2>&1; then
  echo "!!! still present after 160 s: the worker did not finish. Manual cleanup now."
  kill -CONT "$VMPID"; kill -9 "$VMPID"
fi
echo "--- delete: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
