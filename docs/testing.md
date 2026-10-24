# Testing

## Automated tests (no KVM needed)

From the `src/` folder:

```
python -m pytest -q
```

Result on the development machine: **77 passed** in about 7.5 s
(Python 3.14.8, pytest 9.1.1). One harmless Starlette deprecation warning
about `httpx` appears.

| File | What it covers |
|---|---|
| `controller/test_scheduler.py` | Most memory wins, only-one-fits, nobody fits, unhealthy skipped, exact fit, stable tie-break. |
| `controller/test_database.py` | Node and VM rows, unknown column rejected, foreign key enforced, decisions stored. |
| `controller/test_vm_service.py` | Placement, refusal falls through to the next node, both refuse (reasons reported, `refused:` label), unreachable worker marked unhealthy, memory reservation, other worker errors. |
| `controller/test_lifecycle.py` | Create, stop, start, list, delete; delete when the worker lost the VM; unknown VM; stop on an unreachable node keeps the row. |
| `controller/test_reconcile.py` | Unhealthy node -> `UNKNOWN`, resync on return, old orphan deleted, young orphan kept, stale `PENDING` fails, VM gone from worker fails. |
| `controller/test_api.py` | Every route needs a token; `/health` is open; request validation; id patterns. |
| `controller/test_api_errors.py` | Error mapping: 404, 409 (with decision), 502, 503, 204; decisions limit clamping. |
| `worker/test_vm_manager.py` | Stop escalation: graceful, SIGTERM, a frozen VMM killed with SIGKILL and reaped (no zombie), pid-reuse guard, slot exhaustion and reuse. |

The controller tests replace the worker with an in-process fake. The worker
tests use a harmless `sleep` process as a stand-in for the VMM. Neither starts
a real VM, so these tests prove the logic, not the real hypervisor.

## Integration tests (need the running cluster)

```
PS023_INTEGRATION=1 PS023_API_TOKEN=<token> python -m pytest tests/integration -v
```

They are skipped unless `PS023_INTEGRATION=1` is set. On a freshly started
cluster: **3 passed, 1 skipped** in about 42 s. The skipped test checks the
409 insufficient-memory path and skips itself when a node can fit the largest
allowed VM (8192 MB).

Covered: health and auth, both nodes healthy, a real create/stop/start/delete
through the controller, the recorded placement decision matches the node with
the most memory, and the number of host VMM processes is unchanged afterwards.

## Manual failure tests

These inject real failures (`kill`, `ip link del`), so they are run by hand
from `tests/manual/`. Results observed on the development machine:

| Scenario | Result |
|---|---|
| Worker crash | VMs keep running; status `UNKNOWN` after about 15 s; recovers when the worker returns. |
| Cloud Hypervisor `SIGKILL` | VM shows `STOPPED` within 5 s; restart works. |
| Frozen VMM | Escalates to `SIGKILL` in about 75 s; no zombie left. |
| Failover | Node A down; the VM is placed on node B (nested VM); ping, SSH and a web server are reachable from the host. |
| Insufficient memory | `409` with the decision recorded. |
| Worker refusal | Node B without TAP devices: `409`, `no node accepted the VM: node-b: tapvm0 missing: create the TAP pool first`; node B labelled `refused:` and `healthy: true`; no VM left behind. |
| Cold start | After a laptop reboot, `bring-up.sh` rebuilt the network, node B, both workers and the controller; both nodes `HEALTHY`. |

## Known limits of the tests

* The integration leak check counts only host VMM processes, so a leak on
  node B (the nested VM) is not seen by the automated check.
* The worker's `create` and `start` (disk images, cloud-init, a real
  `cloud-hypervisor`) are covered only by the integration and manual tests.
