# Deployment and restart

This describes how the runtime is started on the development laptop. The
scripts use the folder `~/ps023` (the repository copy under `src/` is the same
code, but `bring-up.sh` runs from `~/ps023`).

Not covered here: building the base VM image, the node B kernel and node B's
disk. Those are one-time setup steps.

## Prerequisites

* Linux with `/dev/kvm`; Cloud Hypervisor v54.0.0 on the host and a static
  `cloud-hypervisor` binary inside node B.
* A Python virtual environment at `~/ps023/.venv` with `src/requirements.txt`
  installed.
* `sudo`, `ip`, `iptables`, `curl`, `sshpass` and `python3`. `firewall-cmd` is
  used if present.
* `~/ps023/secrets.env` (mode 600, never committed) defining
  `PS023_VM_PASSWORD`, `PS023_API_TOKEN`, `PS023_TOKEN_NODE_A` and
  `PS023_TOKEN_NODE_B`. The script refuses to run if one is empty.
* `~/ps023/outer/` with `start-outer.sh`, `inner-net.sh` and `start-worker.sh`
  (copies are in `src/scripts/`).

## Start everything (also after a reboot)

```
bash ~/ps023/with-secrets.sh bash ~/ps023/bring-up.sh
```

It asks for the sudo password and takes a few minutes when node B has to boot.
It is safe to run again. It ends with `READY` when both nodes are `HEALTHY`.

| Stage | What it does |
|---|---|
| 1. host network | Creates bridge `br-ps023` (192.168.100.1/24) and TAP devices `tapvm0`-`tapvm7`; enables IP forwarding; adds firewall rules (including Docker's `DOCKER-USER` chain, whose default drop otherwise breaks VM NAT). |
| 2. node B | Starts the nested VM (192.168.100.17, TAP `tapvm7`) and waits for SSH. |
| 3. node B inner network and worker | Recreates node B's inner bridge `br-inner` (10.77.0.1/24) and TAPs `tapvm0`-`tapvm3` (they are lost whenever node B restarts), then starts worker B on port 8002. |
| 4. route | Adds `10.77.0.0/24 via 192.168.100.17` on the host so the host can reach VMs running inside node B. |
| 5. worker A and controller | Stops and restarts worker A (127.0.0.1:8001, slots 0-3) and the controller (127.0.0.1:8000). |
| 6. cluster state | Prints each node's status and memory and the number of host VMM processes (1 expected: node B). |

Running it again restarts worker A and the controller. Running VMs are not
stopped, because each VMM runs in its own session; the controller re-syncs
their state afterwards.

## Stop

```
kill (pgrep -f 'uvicorn main:app.*--port 8001')   # fish shell
kill (pgrep -f 'uvicorn main:app.*--port 8000')
```

VMs keep running; the controller marks them `UNKNOWN` until it can reach their
worker again.

## Logs

`~/ps023/logs/worker-a.log` and `~/ps023/logs/controller.log` on the host;
worker B's log is `~/worker.log` inside node B. Each VM's folder holds a
`vmm.log`.

## Verified

* Warm re-run of `bring-up.sh` with node B already running: several times.
* Cold start after a reboot (everything down): once; the log was kept.
* Nodes were `HEALTHY` and a VM could be created, stopped, started and deleted
  afterwards.

## Common problems

| Symptom | Likely cause |
|---|---|
| `Connection refused` on port 8000 | The controller is not running; run `bring-up.sh`. |
| `worker B not answering` | Look at the end of `~/worker.log` inside node B. |
| Warning that `wlp3s0` is not found | The Wi-Fi interface has another name (check `ip -br addr`). The script only warns. |
| A create is refused with `tapvm0 missing` | Node B's inner TAPs are gone (node B restarted); run `bring-up.sh`. |
