#!/bin/bash
URL=http://192.168.100.17:8002
TOK="${PS023_TOKEN_NODE_B:?set PS023_TOKEN_NODE_B}"
H="Authorization: Bearer $TOK"
echo "--- node-b health: $(curl -s -m 5 $URL/health)"
echo "--- creating a VM directly on node-b (waits up to 180 s)"
curl -s -m 180 -o /tmp/nodeb-create.json -w "HTTP %{http_code} in %{time_total}s\n" \
  -X POST -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"direct01","vcpus":1,"memory_mb":512,"disk_gb":4}' $URL/vms
cat /tmp/nodeb-create.json; echo
ID=$(python3 -c "import json; print(json.load(open('/tmp/nodeb-create.json')).get('id',''))" 2>/dev/null)
if [ -n "$ID" ]; then
  echo "--- created $ID; deleting"
  echo "delete: $(curl -s -m 120 -o /dev/null -w '%{http_code}' -X DELETE -H "$H" $URL/vms/$ID)  (want 204)"
fi
echo "--- vms left on node-b: $(curl -s -m 10 -H "$H" $URL/vms)"
