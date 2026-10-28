# PS-023: Minimal Two-Node Cloud Hypervisor VM Controller

Team TC246. Category: Cloud Computing.

> DRAFT. Section order follows a standard report layout. It must be mapped
> onto `Proposed-structure-hackathon.pdf` once those headings are known.
> Items in [square brackets] are placeholders to be filled or confirmed.

## 1. Summary

We built a central controller and two worker agents that create, start, stop,
delete and list virtual machines through the Cloud Hypervisor API. The
controller authenticates users with a bearer token, places each VM on the node
with the most schedulable memory, records every placement decision, and
reconciles its database with what the workers actually run. Workers escalate a
stop from a guest power-off to SIGKILL and reap the process, so no VMM is left
behind. A small web dashboard and a browser terminal were added on top of the
same API.

**Important limit of our environment:** we had one physical Linux machine.
Node A is a worker on it; node B is a nested VM on the same machine running its
own Cloud Hypervisor and worker. The two nodes are not two separate physical
hosts.

## 2. Requirements and status

| Requirement | Status |
|---|---|
| 2 `/dev/kvm` hosts with preconfigured networking | **Partly met.** Two worker nodes, but node B is a nested VM on the same laptop. [Mentor answer: ...] |
| 1 prepared VM image | Met: Ubuntu 24.04 raw image with cloud-init. |
| Controller + 2 worker agents | Met. |
| VM create, start, stop, list | Met, plus delete. |
| Authenticated controller-to-worker API | Met: a separate bearer token per worker. Plain HTTP; no TLS. |
| Placement by available memory | Met. |
| Enforce resource limits | **Partly met.** vCPUs, memory and disk are validated and passed to Cloud Hypervisor; cgroup limits are not implemented. [Mentor answer: ...] |
| Handle API failures, clean up VM processes without leaks | Met; see section 6. |
| Lifecycle and two-host placement tests | Met: 87 automated tests, integration tests, manual failure tests. |
| Report and demo | This report; demo script in `docs/demo-script.md`. |

Not implemented: TLS/mTLS, cgroup limits, live migration, distributed storage,
more than one VM image, choosing a node for a VM.

## 3. Environment

* Laptop: ASUS TUF A15, Ryzen 7 7445HS (12 threads), 16 GB RAM, Fedora, Cloud
  Hypervisor v54.0.0, Python 3.14.
* Node A: worker on the host, `127.0.0.1:8001`, TAP devices `tapvm0-3`, VM IPs
  192.168.100.10-13.
* Node B: a nested VM (4 vCPU, 4 GB RAM, nested virtualisation enabled) at
  192.168.100.17 with its own Cloud Hypervisor binary and worker on port 8002.
  Its VMs sit on an inner network 10.77.0.0/24 reached from the host through a
  static route.
* Network: bridge `br-ps023` (192.168.100.1/24) with a TAP pool.
* `bring-up.sh` rebuilds the whole runtime after a reboot; a cold start was
  observed twice.

## 4. Architecture

See `docs/architecture.md` for the diagram and component details.

* **Controller** (FastAPI, SQLite): REST API, scheduler, node poller (every
  5 s; a node is `UNHEALTHY` after 15 s without a heartbeat), reconcile loop,
  dashboard and terminal relay.
* **Worker** (FastAPI): one per node. It owns each VM's folder (disk reflinked
  from the base image, cloud-init seed, unix socket) and talks to Cloud
  Hypervisor through that socket.
* **Authentication:** users send `Authorization: Bearer <token>` to the
  controller. The controller uses a different token for each worker. Tokens
  are compared in constant time, and `/health` is the only open route.

## 5. Design decisions

**Placement.** The node with the most schedulable memory wins; the node id
breaks ties so the result is stable. Memory already promised to `PENDING`,
`RUNNING` and `UNKNOWN` VMs is subtracted, so two quick requests cannot
overcommit one node. Every decision is stored with all candidates and a
verdict for each (`eligible`, `skipped: unhealthy`, `skipped: not enough
memory`, `refused: <reason>`).

**Refusals.** A worker answers HTTP 409 if it cannot take a VM (not enough
memory, no free slot, missing TAP device). The controller then tries the next
node; if every node refuses, the API returns 409 and the message names each
node and its reason.

**Resource limits.** The API accepts 1-8 vCPUs, 128-8192 MB memory and 1-50 GB
disk. Names and ids are validated by pattern because they end up in file paths
and cloud-init. Each worker also refuses a VM larger than its own schedulable
memory.

**Failure handling.**

| Failure | Behaviour |
|---|---|
| Worker process crashes | VMs keep running (each VMM runs in its own session). After about 15 s the controller marks the node `UNHEALTHY` and its VMs `UNKNOWN`; they resync when the worker returns. |
| VMM killed | The VM shows `STOPPED` within 5 s and can be restarted. |
| VMM frozen | Stop escalates: power button (30 s), API shutdown (5 s), SIGTERM (5 s), SIGKILL (5 s), then the child is reaped. Measured: stop returned in 70 s, no process left. |
| Worker unreachable during create | The pending row is removed, the node is marked `UNHEALTHY`, and another node is tried. |
| Abandoned records | `PENDING` rows older than 120 s become `FAILED`; unknown worker VMs older than 120 s are deleted. |

## 6. Testing and results

See `docs/testing.md`.

* 87 automated tests pass in about 8 s without KVM (scheduler, database,
  placement and refusal, lifecycle, reconcile, authentication and validation,
  error mapping, terminal relay, stop escalation including a frozen process).
* 4 opt-in integration tests against the live cluster (3 passed, 1 skipped by
  design when a node can fit the largest VM).
* Manual failure tests with saved output in `evidence/`.

The automated tests use fakes for the workers and for SSH, so they prove the
logic. Real-hypervisor behaviour is shown by the integration and manual tests.

## 7. Dashboard and terminal

A single page at `/dashboard/` shows nodes, VMs and recent placement
decisions, with create, start, stop and delete buttons. A Terminal button opens
a shell on a running VM through a WebSocket on the controller that relays to
SSH. See `docs/dashboard.md`. [Confirm: the terminal was checked on a real VM
in the browser.]

## 8. Limitations

* One physical machine: node B is nested, so we did not test across separate
  hosts or a real network.
* Plain HTTP between components; the terminal sends the API token over the
  same plain connection. Suitable for a private network only.
* A frozen VMM makes its whole node look `UNHEALTHY` for about 70 s, because
  the worker's status calls wait on the frozen process. No process leaks; the
  cause is inferred from the code and timings. A short per-VM status timeout
  would fix it.
* Anyone with the API token can open a shell on a running VM.
* The integration leak check only counts VMM processes on the host.
* Every VM uses the one prepared Ubuntu image, and placement is automatic.

## 9. Future work

TLS between components and in front of the dashboard; cgroup limits per VMM;
a per-VM status timeout; choosing a node or an image per request; running node
B on a separate physical host.

## 10. How to run

See `docs/deployment.md`. After a reboot: `bash ~/ps023/with-secrets.sh bash
~/ps023/bring-up.sh`. Tests: `python -m pytest -q` from `src/`.

## Appendix: pseudocode

See `docs/pseudocode.md` (placement with refusal handling, and the stop
escalation).
