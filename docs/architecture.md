# Architecture

## Overview

One central **controller** and two **worker agents** manage VMs through the
Cloud Hypervisor API.

```
            user (bearer token)
                   |
                   v
   +-------------------------------+
   | Controller  (FastAPI :8000)   |
   |  scheduler, SQLite, poller,   |
   |  reconcile                    |
   +---------+-------------+-------+
             | HTTP + per-worker bearer token
     +-------+---+     +---+---------------+
     | Worker A  |     | Worker B          |
     | host      |     | inside node-b     |
     | :8001     |     | 192.168.100.17:8002|
     +-----+-----+     +-------+-----------+
           |                   |
   cloud-hypervisor      cloud-hypervisor
   (one VMM per VM)      (one VMM per VM)
```

## Test setup (important)

* **Node A** is a worker on the host laptop (Fedora, `/dev/kvm`).
* **Node B is a nested VM on the same physical laptop** (nested KVM, 4 vCPU,
  4 GB RAM). It runs its own Cloud Hypervisor and its own worker. The project
  was built and tested on one physical machine, so the two nodes are **not**
  two separate physical hosts.
* Controller-to-worker traffic is **plain HTTP with a per-worker bearer token
  on a private virtual network**. TLS/mTLS is not implemented.

## Controller

* FastAPI on `127.0.0.1:8000`, SQLite database, bearer-token user
  authentication on every route except `/health`.
* **Scheduler**: the node with the most schedulable memory wins; `node_id`
  breaks ties. Memory is reserved for VMs in `PENDING`, `RUNNING` and
  `UNKNOWN` state. Unhealthy nodes are skipped.
* **Decisions table**: every placement decision is stored, including all
  candidates and why each was eligible or skipped.
* **Refusals**: if a worker refuses a create (HTTP 409), the controller tries
  the next node. If every node refuses, the API returns 409 and the reason
  names each node (for example `node-b: tapvm0 missing`). A refusing node is
  labelled `refused: <reason>` in the decision and stays `healthy: true`.
* **Poller**: every 5 s; a node is `UNHEALTHY` after 15 s without a heartbeat.
* **Reconcile**: runs after each poll.
  * Node unhealthy: its `RUNNING`/`STOPPED` VMs become `UNKNOWN`.
  * Node returns: VM state is re-synced from the worker.
  * Worker VMs the controller does not know, older than 120 s, are deleted
    (orphans).
  * `PENDING` rows older than 120 s become `FAILED`.
  * A VM missing from its worker for more than 60 s becomes `FAILED`.

## Worker

* FastAPI with its own bearer token per worker.
* Each VM has its own folder: a disk reflinked from the base image, a
  cloud-init seed with a unique instance id, and a unix socket for the
  Cloud Hypervisor API.
* The VMM is started with `start_new_session=True`. Running VMs survive a
  worker restart on node A, and on node B only when the systemd unit specifies
  `KillMode=process` (pending live verification on the cloud instance).
* **Stop escalation**: power button (up to 30 s) -> `vm.shutdown` +
  `vmm.shutdown` (5 s) -> `SIGTERM` (5 s) -> `SIGKILL` (5 s). The child
  process is then reaped, so no zombie remains.
* A pid file is trusted only if the process command line contains the VM's
  own socket path (guards against pid reuse).
* Requests are validated: VM names, ids and sizes (1-8 vCPUs, 128-8192 MB
  memory, 1-50 GB disk).

## Resource limits and cgroups v2

Requested vCPUs, memory, and disk are validated by the controller and passed to
Cloud Hypervisor. Resource limits are strictly enforced on each worker using
cgroups v2:
* **Delegated Subtree**: The worker runs unprivileged under systemd / cgroups v2.
  To satisfy the cgroup v2 "no internal processes" rule, the worker moves itself
  into a child cgroup (`worker/`), enables `cpu`, `memory`, and `pids` controllers
  in `cgroup.subtree_control`, and creates each VM in a sibling cgroup (`ps023-vmm-<vm_id>`).
* **Fallback Strategy**: If the worker is launched interactively in a shared terminal
  scope (e.g., `kitty-*.scope`), enabling controllers on the scope fails due to sibling
  processes; the manager automatically falls back to delegating from the parent
  `app.slice` which has controllers enabled. If delegation cannot be verified by
  reading back `cgroup.subtree_control`, enforcement gracefully falls back to disabled
  with a warning, never blocking VM launch.
* **Limit Calculations**:
  * `memory.max`: guest RAM (`memory_mb`) + fixed overhead (default 128 MB, configurable via `PS023_CGROUP_MEMORY_OVERHEAD_MB`).
  * `cpu.max`: quota = `vcpus * 100000 * headroom` with period 100000 (default headroom 1.25, configurable via `PS023_CGROUP_CPU_HEADROOM`).
  * `pids.max`: minimum 256 or `vcpus * 16` (default 256, configurable via `PS023_CGROUP_PIDS_MIN`).
  * All defaults are unmeasured engineering estimates until profiled under production workloads.
* **Read-Back Verification**: Limit values are confirmed by reading back from the kernel
  cgroup files (`memory.max`, `cpu.max`, `pids.max`) before reporting enforcement.
* **Process Lifecycle & Cleanup**: On VM stop, cgroups are reset to unenforced.
  Cgroups are removed via `rmdir` only after the VMM process has been fully reaped,
  retrying on `EBUSY` and tolerating `ENOENT`. Empty leftover cgroups are periodically
  pruned with a 10 s age threshold to avoid racing with concurrent VM creation.

## Not implemented

TLS/mTLS, live migration, distributed storage.
