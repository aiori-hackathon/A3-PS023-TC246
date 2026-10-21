#!/bin/bash
TOK="${PS023_TOKEN_NODE_B:?set PS023_TOKEN_NODE_B}"
export SSHPASS="${PS023_VM_PASSWORD:?set PS023_VM_PASSWORD}"
URL=http://192.168.100.17:8002
H="Authorization: Bearer $TOK"

curl -s -m 120 -o /tmp/inner-create.json -X POST -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"web-inner","vcpus":1,"memory_mb":512,"disk_gb":4}' $URL/vms
ID=$(python3 -c "import json; print(json.load(open('/tmp/inner-create.json'))['id'])") \
  || { cat /tmp/inner-create.json; echo; exit 1; }
IP=$(python3 -c "import json; print(json.load(open('/tmp/inner-create.json'))['ip'])")
echo "created $ID at $IP"

for i in $(seq 1 60); do (echo > /dev/tcp/$IP/22) 2>/dev/null && break; sleep 1; done
echo "ping from the host: $(ping -c 2 -W 1 $IP | tail -n 1)"
sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null rajyavardhan@$IP \
  'hostname; setsid python3 -m http.server 8080 > /tmp/http.log 2>&1 < /dev/null & sleep 1; echo web server started'
echo "--- fetched from the host:"
curl -s -m 5 http://$IP:8080 | head -n 4
echo "--- delete: $(curl -s -m 120 -o /dev/null -w '%{http_code}' -X DELETE -H "$H" $URL/vms/$ID)  (want 204)"
