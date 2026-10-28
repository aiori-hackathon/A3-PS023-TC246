# Evidence

Raw output from runs on the development laptop (one physical machine; node B
is a nested VM on it). Files are copied unedited.

| File | Date | What it shows |
|---|---|---|
| `bring-up.log` | 23 Oct | First run of `bring-up.sh` with node B already running: both nodes `HEALTHY`, one host VMM. |
| `bring-up3.log` | 23 Oct | **Cold start** after a laptop reboot: the script started node B (`started, pid ...`), rebuilt its inner network, started both workers and the controller. Both nodes `HEALTHY`. |
| `bring-up4.log` | 24 Oct | A second cold start, same result. |
| `evidence-stuck-stop.log` | 24 Oct | Frozen VMM (`SIGSTOP`) test: the controller answered `HTTP 200` after 70 s, the VMM process was gone, the VM was deleted afterwards (`204`). |
| `evidence-decisions.json` | 24 Oct | The last four stored placement decisions, including one refusal: node B refused with `tapvm0 missing` and is labelled `refused:` while `healthy: true`; node A is `skipped: unhealthy` (its worker was stopped for that test). The `vm-da47c83a` decision from the frozen-VMM run shows node A as `skipped: unhealthy` while its worker process was running. |
| `pytest-unit.log` | see file | Output of `python -m pytest -v` for the automated tests. |

Manual failure tests (worker crash, VMM kill, failover to node B) were run
from `src/tests/manual/`; their results are summarised in `docs/testing.md`.
