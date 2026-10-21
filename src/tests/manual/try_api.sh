#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000
j() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

echo "--- health / auth"
curl -s $BASE/health; echo
echo "no token: $(curl -s -o /dev/null -w '%{http_code}' $BASE/nodes)  (want 401)"
echo "nodes: $(curl -s -H "$API" $BASE/nodes | python3 -c 'import sys,json; print([(n["id"],n["status"]) for n in json.load(sys.stdin)])')"

echo "--- create"
RESP=$(curl -s -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"web01","vcpus":1,"memory_mb":1024,"disk_gb":4}' $BASE/vms)
echo "$RESP"
ID=$(echo "$RESP" | j "['id']") || { echo "CREATE FAILED, stopping"; exit 1; }
echo "id: $ID"

sleep 12
echo "--- stop";   curl -s -X POST -H "$API" $BASE/vms/$ID/stop  | j "['status']"
echo "--- start";  curl -s -X POST -H "$API" $BASE/vms/$ID/start | j "['status']"
echo "--- decision"; curl -s -H "$API" "$BASE/decisions?limit=1"; echo
sleep 12
echo "--- delete: $(curl -s -X DELETE -o /dev/null -w '%{http_code}' -H "$API" $BASE/vms/$ID)  (want 204)"
echo "--- vms left: $(curl -s -H "$API" $BASE/vms)  (want [])"
