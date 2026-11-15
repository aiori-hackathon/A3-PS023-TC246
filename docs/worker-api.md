# Worker API

Each worker is a FastAPI app in front of `VMManager`. The controller is its
only intended caller; users talk to the controller.

Authentication: `Authorization: Bearer <worker token>`. Each worker has its
own token (`PS023_WORKER_TOKEN`). `GET /health` needs no token.

| Method | Path | Success | Notes |
|---|---|---|---|
| GET | `/health` | 200 | `{"status": "ok", "node_id": "..."}`. No token. |
| GET | `/resources` | 200 | Node resources; includes `memory_schedulable_mb`. |
| GET | `/vms` | 200 | All VMs on this worker with live status. |
| GET | `/vms/{vm_id}` | 200 | `404` if unknown. |
| POST | `/vms` | 201 | Create (and by default start) a VM. |
| POST | `/vms/{vm_id}/start` | 200 | Returns the VM. |
| POST | `/vms/{vm_id}/stop` | 200 | Returns the VM plus `stopped_via`. |
| DELETE | `/vms/{vm_id}` | 204 | Stops the VM (10 s graceful), then removes its folder. |

`stopped_via` is one of `graceful`, `forced-api`, `sigterm`, `sigkill`,
`already-stopped`.

## Create

```json
{"name": "web01", "vcpus": 1, "memory_mb": 512, "disk_gb": 4, "start": true}
```

Same limits as the controller: `vcpus` 1-8, `memory_mb` 128-8192,
`disk_gb` 1-50, `name` a safe hostname (it goes into cloud-init). `vm_id` must
match `vm-` plus 8 hex digits because ids become file paths.

Before creating anything the worker compares `memory_mb` with its own
schedulable memory and answers `409` if it does not fit:
`insufficient memory: requested X MB, schedulable Y MB`.

If creating or starting the VM fails, the worker deletes it again, so no
half-made VM is left behind.

## Errors

| Code | Meaning |
|---|---|
| 401 | Missing or invalid bearer token. |
| 404 | Unknown VM (`unknown vm ...`). |
| 409 | The worker refuses: not enough memory, no free slot, or a setup problem such as a missing TAP device. The controller treats any `409` from a create as a refusal and tries another node. |
| 422 | Request validation failed. |

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PS023_NODE_ID` | `node-a` | Name this worker reports. |
| `PS023_WORKER_TOKEN` | none (required) | Bearer token the controller must send. |
| `PS023_VM_PASSWORD` | none | Login password set for the VM user by cloud-init. |
| `PS023_VM_ROOT` | `~/ps023/vms` | One folder per VM lives here. |
| `PS023_BASE_IMAGE` | `~/ps023/lab/images/ubuntu-noble.raw` | Prepared Ubuntu 24.04 raw image. |
| `PS023_KERNEL` | `~/ps023/lab/kernel/vmlinux.bin` | Kernel passed to Cloud Hypervisor. |
| `PS023_SUBNET` | `192.168.100` | First three octets of the VM network; the gateway is `.1`. |
| `PS023_SLOT_START` | `0` | First slot number. |
| `PS023_SLOT_COUNT` | `8` | Number of slots. |
| `PS023_CGROUPS` | `on` | Set to `off` to disable cgroup limits entirely. |
| `PS023_CGROUP_ROOT` | none (auto-derived) | Root cgroup; auto-derived from `/proc/self/cgroup`. |
| `PS023_CGROUP_MEMORY_OVERHEAD_MB` | `128` | Fixed memory overhead for VMM process (unmeasured default). |
| `PS023_CGROUP_PIDS_MIN` | `256` | Minimum PID limit for VMM tree (unmeasured default). |
| `PS023_CGROUP_CPU_HEADROOM` | `1.25` | CPU quota headroom multiplier (unmeasured default). |

Each VM takes one slot, which fixes its TAP device (`tapvmN`) and its IP. When
all slots are in use, create is refused with `409`. In the development setup
node A uses slots 0-3 (VM IPs 192.168.100.10-13).

## Cgroups v2 Enforcement

* On start, the worker creates a dedicated child cgroup `ps023-vmm-<vm_id>` with:
  * `memory.max`: `(memory_mb + PS023_CGROUP_MEMORY_OVERHEAD_MB) * 1024 * 1024` bytes.
  * `cpu.max`: `quota period` where `quota = vcpus * 100000 * PS023_CGROUP_CPU_HEADROOM`, `period = 100000`.
  * `pids.max`: `max(PS023_CGROUP_PIDS_MIN, vcpus * 16)`.
* Limits are strictly verified by reading back values from the filesystem before reporting `cgroups: true`.
* If cgroup setup or attach fails, the VM starts unrestricted (`cgroups: false`), and empty directories are cleaned up immediately.
* On stop and delete, the cgroup is removed after the VMM process is reaped (with EBUSY retries and ENOENT tolerance).
* Existing running VMs default to `cgroups: false` without retrofitting.

## Process handling

* The VMM runs in its own session, so VMs keep running if the worker restarts.
* A VMM is considered alive only if its pid file points to a live process
  whose command line contains this VM's socket path.
* Stop order: power button (30 s) -> `vm.shutdown` and `vmm.shutdown` (5 s) ->
  `SIGTERM` (5 s) -> `SIGKILL` (5 s). The child is then reaped.
