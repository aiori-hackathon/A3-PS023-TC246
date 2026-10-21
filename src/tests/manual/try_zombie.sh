#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000

RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"zombie","vcpus":1,"memory_mb":512,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
WID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['worker_vm_id'])")
NODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")
DIR=$([ "$NODE" = "node-a" ] && echo "$HOME/ps023/vms" || echo "$HOME/ps023/vms-b")
echo "created $ID on $NODE (worker id $WID)"
sleep 12

VMPID=$(pgrep -f "api-socket path=.*$WID/vm.sock" | head -n 1)
[ -n "$VMPID" ] || { echo "VMM process not found, stopping"; exit 1; }
echo "VMM pid $VMPID, parent: $(ps -o ppid= -p $VMPID | tr -d ' ')"
echo "worker pids: $(pgrep -f 'uvicorn main:app --host 127.0.0.1 --port 800[12]' | tr '\n' ' ')"
kill -STOP "$VMPID"
echo ">>> frozen. asking for stop (up to 100 s)"

T0=$(date +%s)
curl -s -m 110 -o /tmp/zombie-stop.json -w ">>> controller answered HTTP %{http_code}\n" \
  -X POST -H "$API" $BASE/vms/$ID/stop &

for i in $(seq 1 30); do
  ST=$(ps -o stat= -p "$VMPID" 2>/dev/null | tr -d ' ')
  PIDF=$([ -f "$DIR/$WID/vmm.pid" ] && echo present || echo absent)
  echo "t=$(( $(date +%s) - T0 ))s state=[${ST:-gone}] vmm.pid file=$PIDF"
  [ -z "$ST" ] && break
  sleep 5
done
wait
echo "--- final controller reply:"; cat /tmp/zombie-stop.json; echo
echo "--- delete: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
