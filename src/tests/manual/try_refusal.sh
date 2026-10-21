#!/bin/bash
API="Authorization: Bearer ${PS023_API_TOKEN:?set PS023_API_TOKEN}"
BASE=http://127.0.0.1:8000
echo "--- node states before the create:"
curl -s -H "$API" $BASE/nodes | python3 -c "import sys,json; [print(n['id'], n['status']) for n in json.load(sys.stdin)]"
echo "--- create (want: node-a UNHEALTHY, node-b HEALTHY but with no TAP devices):"
curl -s -m 60 -w '\nHTTP %{http_code}\n' -X POST -H "$API" -H 'Content-Type: application/json' \
  -d '{"name":"refuse01","vcpus":1,"memory_mb":512,"disk_gb":4}' $BASE/vms
