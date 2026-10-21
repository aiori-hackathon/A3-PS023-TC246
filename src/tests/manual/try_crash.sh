#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000

RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"crash01","vcpus":1,"memory_mb":512,"disk_gb":4}' $BASE/vms)
ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])") \
  || { echo "CREATE FAILED: $RESP"; exit 1; }
NODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")
echo "created $ID on $NODE"

sleep 12   # let the guest boot
PORT=$([ "$NODE" = "node-a" ] && echo 8001 || echo 8002)
PID=$(pgrep -f "uvicorn main:app --host 127.0.0.1 --port $PORT" | head -n 1)
[ -n "$PID" ] || { echo "worker process not found, stopping"; exit 1; }
echo ">>> killing $NODE worker (pid $PID, port $PORT)"
kill "$PID" || { echo "kill failed, stopping"; exit 1; }
echo ">>> restart $NODE in its terminal once the status shows UNKNOWN"

for i in $(seq 1 30); do
  S=$(curl -s -H "$API" $BASE/vms/$ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d['node_id'])")
  echo "$(date +%T) $S   vmm-processes=$(pgrep -fc cloud-hypervisor)"
  sleep 5
done
echo "--- cleanup: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
