#!/bin/bash
# Rebuilds the whole PS-023 runtime after a reboot. Safe to run again.
P=$HOME/ps023
LOG=$P/logs
VENV=$P/.venv/bin
SECRETS=$P/secrets.env
NODEB=192.168.100.17
mkdir -p "$LOG"

[ -f "$SECRETS" ] || { echo "missing $SECRETS"; exit 1; }
. "$SECRETS"   # plain shell variables, deliberately NOT exported
for v in PS023_VM_PASSWORD PS023_API_TOKEN PS023_TOKEN_NODE_A PS023_TOKEN_NODE_B; do
  [ -n "${!v}" ] || { echo "$v is empty in $SECRETS"; exit 1; }
done
step() { echo; echo "=== $*"; }
sudo -v || exit 1

step "1. host network"
ip -br addr show wlp3s0 >/dev/null 2>&1 || echo "WARNING: wlp3s0 not found; check the Wi-Fi name"
ip link show br-ps023 >/dev/null 2>&1 || {
  sudo ip link add br-ps023 type bridge
  sudo ip addr add 192.168.100.1/24 dev br-ps023
}
sudo ip link set br-ps023 up
for n in 0 1 2 3 4 5 6 7; do
  ip link show tapvm$n >/dev/null 2>&1 || sudo ip tuntap add dev tapvm$n mode tap user "$USER"
  sudo ip link set tapvm$n master br-ps023
  sudo ip link set tapvm$n up
done
sudo sysctl -qw net.ipv4.ip_forward=1
sudo firewall-cmd --zone=trusted --add-interface=br-ps023 >/dev/null 2>&1 || true
sudo firewall-cmd --zone=FedoraWorkstation --add-masquerade >/dev/null 2>&1 || true
if sudo iptables -S DOCKER-USER >/dev/null 2>&1; then
  sudo iptables -C DOCKER-USER -i br-ps023 -j ACCEPT 2>/dev/null || sudo iptables -I DOCKER-USER -i br-ps023 -j ACCEPT
  sudo iptables -C DOCKER-USER -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || sudo iptables -I DOCKER-USER -o br-ps023 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
fi
echo "bridge and $(ip -br link show master br-ps023 | wc -l) TAP devices ready"

step "2. node-b (nested VM)"
bash "$P/outer/start-outer.sh"
nb() { SSHPASS="$PS023_VM_PASSWORD" sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o ServerAliveInterval=10 rajyavardhan@$NODEB "$@"; }
for i in $(seq 1 30); do nb true 2>/dev/null && break; sleep 2; done
nb hostname || { echo "cannot ssh to node-b; see $P/outer/serial.log and vmm.log"; exit 1; }

step "3. node-b inner network and worker"
nb 'bash -s' < "$P/outer/inner-net.sh" >/dev/null || { echo "inner network setup failed"; exit 1; }
nb 'bash -s' < "$P/outer/start-worker.sh" >/dev/null 2>&1
for i in $(seq 1 20); do curl -s -m 2 http://$NODEB:8002/health | grep -q node-b && break; sleep 1; done
curl -s -m 3 http://$NODEB:8002/health | grep -q node-b || { echo "worker B not answering; run: nb 'tail -n 20 ~/worker.log'"; exit 1; }
echo "worker B ok"

step "4. route to the inner network"
sudo ip route replace 10.77.0.0/24 via $NODEB
ip route show 10.77.0.0/24

step "5. worker A and controller on the host"
up() { curl -s -m 2 "$1" | grep -q "$2"; }
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8001' 2>/dev/null
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8000' 2>/dev/null
sleep 1
(
  cd "$P/worker" &&
  export PS023_VM_PASSWORD PS023_WORKER_TOKEN="$PS023_TOKEN_NODE_A" PS023_NODE_ID=node-a PS023_SLOT_START=0 PS023_SLOT_COUNT=4
  setsid "$VENV/uvicorn" main:app --host 127.0.0.1 --port 8001 >> "$LOG/worker-a.log" 2>&1 < /dev/null &
)
(
  cd "$P/controller" &&
  export PS023_VM_PASSWORD PS023_API_TOKEN PS023_TOKEN_NODE_A PS023_TOKEN_NODE_B PS023_NODES="node-a=http://127.0.0.1:8001,node-b=http://$NODEB:8002"
  setsid "$VENV/uvicorn" main:app --host 127.0.0.1 --port 8000 >> "$LOG/controller.log" 2>&1 < /dev/null &
)
for i in $(seq 1 30); do up http://127.0.0.1:8001/health node-a && up http://127.0.0.1:8000/health ok && break; sleep 1; done
up http://127.0.0.1:8001/health node-a && echo "worker A ok" || { echo "worker A not answering; see $LOG/worker-a.log"; exit 1; }
up http://127.0.0.1:8000/health ok && echo "controller ok" || { echo "controller not answering; see $LOG/controller.log"; exit 1; }

step "6. cluster state"
for i in $(seq 1 20); do
  N=$(curl -s -m 3 -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/nodes | python3 -c 'import sys,json; print(" ".join("%s=%s(%sMB)" % (n["id"], n["status"], n["memory_schedulable_mb"]) for n in json.load(sys.stdin)))' 2>/dev/null)
  echo "$N" | grep -q 'node-a=HEALTHY' && echo "$N" | grep -q 'node-b=HEALTHY' && break
  sleep 2
done
echo "nodes: $N"
echo "host VMMs: $(pgrep -fc '[c]loud-hypervisor') (1 expected: node-b)"
echo
echo "READY. Logs are in $LOG. Run a test with: bash ~/ps023/with-secrets.sh bash ~/ps023/controller/try_api.sh"
