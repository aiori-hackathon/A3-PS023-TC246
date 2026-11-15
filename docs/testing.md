# PS-023: Testing & Verification Guide

## 1. Automated Test Suites

### A. Python Backend Test Suite (`pytest`)
- **Execution Command**:
  ```bash
  .venv/bin/pytest tests/ controller/ worker/
  ```
- **Test Count**: **182 passed, 6 skipped** (0 failures).
- **Coverage**:
  - `controller/`: REST endpoints, authentication bearer middleware, database migrations, scheduler heuristic policies (`memory_aware`, `best_fit`, `first_fit`), node leases, and tombstone reconciliation.
  - `worker/`: VM creation, cgroups v2 limits (`memory.max`, `cpu.max`, `pids.max`), Cloud Hypervisor socket communication, and 4-tier stop escalation.
  - `tests/`: Integration flows, chaos edge cases, and API error specifications (409, 422).

### B. Frontend UI Test Suite (`vitest`)
- **Execution Command**:
  ```bash
  cd frontend && npm test -- --run
  ```
- **Test Count**: **12 passed** (100%).
- **Coverage**: Navigation sidebar tabs, theme switching, real-time node cards, WebSocket terminal integration, and confirmation modals.

---

## 2. Chaos & Failure Benchmarks

### A. Local Fallback Benchmark (6 Runs: 15 Nov 2026)
Source: `evidence/chaos_fallback_repeats_20261115.txt`
- Evaluated 3 runs of mode `worker` and 3 runs of mode `worker-preserve-vms`.
- Detection latency: **13.83 s – 15.70 s**.
- Cold evacuation latency: **0.00 s – 0.70 s**.
- Total recovery: **14.33 s – 16.39 s**.
- Fencing outcome: Stale VMMs terminated cleanly in **2.0 s – 9.33 s** post-return.

### B. Controller Restart Reconciliation Test
Source: `evidence/controller_restart_20261115.txt`
- Controller restart latency: **2.06 s**.
- Pre-restart VMs preserved: 2/2 in `RUNNING` status.
- Zero duplicate or orphan VMs.

### C. End-to-End Rehearsal Automation (3 Runs)
Source: `evidence/demo_rehearsal_run1/2/3_20261115.txt`
- 3 full demo passes executed consecutively through the REST API.
- All runs succeeded with 0 failed steps.
