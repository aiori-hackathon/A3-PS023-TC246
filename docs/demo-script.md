# Demo script (about 10 minutes)

Prepare once, before the session:

```fish
bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh 2>&1 | tail -6
set -x SSHPASS (grep '^PS023_VM_PASSWORD=' ~/ps023/secrets.env | cut -d= -f2-)
```

Open the dashboard at `http://127.0.0.1:8000/dashboard/` and connect with the
API token. Do not show the token on screen.

Fallback if something fails live: show the saved logs in `evidence/` and say
what happened.

## 1. The setup (1 min)

Say, with `docs/architecture.md` on screen: node A is a worker on this laptop,
node B is a nested VM on the same laptop with its own Cloud Hypervisor and
worker. Controller to worker traffic is plain HTTP plus a per-worker bearer
token on a private virtual network.

## 2. Cluster state and authentication (1 min)

```fish
bash ~/ps023/with-secrets.sh bash -c 'curl -s -o /dev/null -w "no token: %{http_code}\n" http://127.0.0.1:8000/nodes; curl -s -H "Authorization: Bearer $PS023_API_TOKEN" http://127.0.0.1:8000/nodes'
```

Expect `no token: 401`, then both nodes `HEALTHY` with free memory.

## 3. VM lifecycle (3 min)

```fish
bash ~/ps023/with-secrets.sh bash ~/ps023/controller/try_api.sh
```

It checks health and auth, creates a VM, stops it, starts it, prints the
placement decision, deletes it and shows the VM list is empty. It takes about
a minute. Then show the same flow in the dashboard (create, terminal, delete).

## 4. Placement decision (1 min)

In the dashboard's "Latest placement decisions", point at one row: both
candidate nodes, their free memory and why one was chosen.

## 5. Failover to node B (2 min)

Stop worker A and create a VM; it must land on node B.

```fish
pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8001'
sleep 20
bash ~/ps023/with-secrets.sh bash -c 'curl -s -m 90 -X POST -H "Authorization: Bearer $PS023_API_TOKEN" -H "Content-Type: application/json" -d "{\"name\":\"failover01\",\"vcpus\":1,\"memory_mb\":512,\"disk_gb\":4}" http://127.0.0.1:8000/vms'
```

Expect `"node_id":"node-b"` and an IP of the form `10.77.0.x`. Then
`ping -c 3 <that IP>`. Afterwards delete the VM from the dashboard and restore
worker A with `bring-up.sh`.

## 6. No leaked processes (optional, 1.5 min)

```fish
bash ~/ps023/with-secrets.sh bash ~/ps023/controller/try_stuck_stop.sh
```

It freezes a VMM and asks the controller to stop it. Expect `HTTP 200 after`
about 70 s, `process ... gone`, and cleanup `204`. Start it, talk while it
runs, then run:

```fish
ps -eo pid,stat,args | grep '[c]loud-hypervisor' | cut -c1-90
```

Only node B's outer VM should be listed, with no `Z` in the state column.

## 7. Tests and pseudocode (1.5 min)

```fish
cd ~/ps023-submit/src; and ~/ps023/.venv/bin/python -m pytest -q
```

Expect `87 passed`. Then show `docs/pseudocode.md`.

## Do not run live

The refusal test needs node B's TAP devices removed (it breaks the cluster
until `bring-up.sh` is run again). Show `evidence/evidence-decisions.json`
instead.
