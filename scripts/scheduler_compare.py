#!/usr/bin/env python3
"""scripts/scheduler_compare.py
Deterministic comparison simulation of PS-023 scheduler policies:
- memory_aware (highest available memory / load spreading)
- first_fit (first healthy node with sufficient memory)
- best_fit (smallest sufficient memory / packing)

SIMULATION ONLY: Pure Python deterministic execution. No live hypervisors or cluster hosts touched.
"""
import sys
import copy
from pathlib import Path

# Add src/controller to path for imports
controller_dir = Path(__file__).resolve().parent.parent / "src" / "controller"
sys.path.insert(0, str(controller_dir))

from scheduler import NodeView, place


def run_simulation(policy_name: str, node_capacities: dict[str, int], workload: list[tuple[str, str, int]]):
    """Replay workload sequence for a given policy.
    
    workload: list of ("CREATE"|"DELETE", vm_id, memory_mb)
    """
    # Track current state: node_id -> remaining_mb
    available = copy.deepcopy(node_capacities)
    running_vms = {}  # vm_id -> (node_id, memory_mb)

    log = []
    placed_count = 0
    refused_count = 0

    for step_num, (action, vm_id, mem_mb) in enumerate(workload, 1):
        if action == "CREATE":
            nodes = [
                NodeView(nid, True, available[nid])
                for nid in sorted(available.keys())
            ]
            d = place(nodes, mem_mb, policy=policy_name)
            if d.selected:
                available[d.selected] -= mem_mb
                running_vms[vm_id] = (d.selected, mem_mb)
                placed_count += 1
                log.append(f"Step {step_num:02d}: CREATE {vm_id} ({mem_mb}MB) -> PLACED on {d.selected} (reason: {d.reason})")
            else:
                refused_count += 1
                log.append(f"Step {step_num:02d}: CREATE {vm_id} ({mem_mb}MB) -> REFUSED (reason: {d.reason})")
        elif action == "DELETE":
            if vm_id in running_vms:
                nid, allocated_mb = running_vms.pop(vm_id)
                available[nid] += allocated_mb
                log.append(f"Step {step_num:02d}: DELETE {vm_id} ({allocated_mb}MB) -> RELEASED on {nid}")
            else:
                log.append(f"Step {step_num:02d}: DELETE {vm_id} -> NOT FOUND (skipped)")

    return {
        "policy": policy_name,
        "placed": placed_count,
        "refused": refused_count,
        "final_available": available,
        "active_vms_count": len(running_vms),
        "log": log,
    }


def main():
    # Initial cluster setup: 3 nodes with varied schedulable capacities
    initial_nodes = {
        "node-a": 8192,
        "node-b": 4096,
        "node-c": 6144,
    }

    # Deterministic sequence of 20 operations
    workload = [
        ("CREATE", "vm-01", 1024),
        ("CREATE", "vm-02", 2048),
        ("CREATE", "vm-03", 512),
        ("CREATE", "vm-04", 4096),
        ("CREATE", "vm-05", 1024),
        ("DELETE", "vm-02", 2048),  # create hole
        ("CREATE", "vm-06", 2048),
        ("CREATE", "vm-07", 1024),
        ("CREATE", "vm-08", 4096),
        ("DELETE", "vm-04", 4096),
        ("CREATE", "vm-09", 512),
        ("CREATE", "vm-10", 2048),
        ("CREATE", "vm-11", 1024),
        ("CREATE", "vm-12", 4096),
        ("DELETE", "vm-01", 1024),
        ("CREATE", "vm-13", 1024),
        ("CREATE", "vm-14", 2048),
        ("CREATE", "vm-15", 4096),  # stress allocation
        ("CREATE", "vm-16", 2048),
        ("DELETE", "vm-08", 4096),
    ]

    header = "=" * 80 + "\n"
    header += "PS-023 SCHEDULER POLICY COMPARISON (SIMULATION)\n"
    header += "Pure Python deterministic workload replay (20 operations)\n"
    header += "STATUS: SIMULATION ONLY (No live hypervisors or cloud VMs modified)\n"
    header += "=" * 80 + "\n\n"
    header += f"Initial Node Schedulable Capacities: {initial_nodes}\n"
    header += f"Total Workload Steps: {len(workload)}\n\n"

    output_lines = [header]

    policies = ["memory_aware", "first_fit", "best_fit"]
    results = {}

    for pol in policies:
        res = run_simulation(pol, initial_nodes, workload)
        results[pol] = res
        output_lines.append(f"--- Policy: {pol} ---\n")
        output_lines.append(f"Summary: Placed={res['placed']}, Refused={res['refused']}, Final Active VMs={res['active_vms_count']}\n")
        output_lines.append(f"Final Node Headroom (MB): {res['final_available']}\n")
        output_lines.append("Execution Trace:\n")
        for line in res["log"]:
            output_lines.append("  " + line + "\n")
        output_lines.append("\n")

    # Comparative analysis summary
    output_lines.append("=" * 80 + "\n")
    output_lines.append("COMPARATIVE POLICY ANALYSIS & INVARIANTS\n")
    output_lines.append("=" * 80 + "\n")
    for pol in policies:
        r = results[pol]
        output_lines.append(f"- {pol:12s}: Placed={r['placed']}, Refused={r['refused']}, Remaining Free Headroom: {r['final_available']}\n")
    output_lines.append("\nObservations:\n")
    output_lines.append("1. memory_aware (default): Spreads allocations to maintain maximum available headroom across all cluster nodes.\n")
    output_lines.append("2. first_fit: Greedily fills the first eligible host in lexical order, clustering allocations on node-a.\n")
    output_lines.append("3. best_fit: Tightly packs microVMs onto the smallest sufficient capacity node, preserving large contiguous memory blocks on larger hosts for high-RAM workloads.\n")
    output_lines.append("=" * 80 + "\n")

    full_report = "".join(output_lines)
    print(full_report)

    # Save to evidence
    evidence_dir = Path(__file__).resolve().parent.parent / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "scheduler_compare_20261114.txt"
    with open(evidence_file, "w") as f:
        f.write(full_report)
    print(f"\nWrote deterministic simulation report to: {evidence_file}")


if __name__ == "__main__":
    main()
