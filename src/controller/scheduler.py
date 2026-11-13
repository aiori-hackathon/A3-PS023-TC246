"""Memory-based VM placement. Pure logic: no network, no database."""
from dataclasses import dataclass, field
import os

POLICIES = ("memory_aware", "first_fit", "best_fit")
DEFAULT_POLICY = "memory_aware"


@dataclass
class NodeView:
    node_id: str
    healthy: bool
    memory_schedulable_mb: int
    vms_running: int = 0


@dataclass
class Decision:
    selected: str | None
    reason: str
    requested_mb: int
    candidates: list = field(default_factory=list)  # one dict per node
    policy: str = DEFAULT_POLICY


def place(nodes, requested_mb, target_node=None, policy=None):
    active_policy = policy or os.environ.get("PS023_SCHEDULER_POLICY") or DEFAULT_POLICY
    if active_policy not in POLICIES:
        active_policy = DEFAULT_POLICY

    candidates = []
    target = None if (not target_node or target_node == "auto") else target_node

    for n in nodes:
        if not n.healthy:
            verdict = "skipped: unhealthy"
        elif n.memory_schedulable_mb < requested_mb:
            verdict = "skipped: not enough memory"
        elif target and n.node_id != target:
            verdict = "skipped: not target node"
        else:
            verdict = "eligible"
        candidates.append({
            "node_id": n.node_id,
            "healthy": n.healthy,
            "available_mb": n.memory_schedulable_mb,
            "verdict": verdict,
        })

    if target:
        matched = [n for n in nodes if n.node_id == target]
        if not matched:
            return Decision(None, f"target node {target} not found",
                            requested_mb, candidates, policy=active_policy)
        tn = matched[0]
        if not tn.healthy:
            return Decision(None, f"target node {target} is unhealthy",
                            requested_mb, candidates, policy=active_policy)
        if tn.memory_schedulable_mb < requested_mb:
            return Decision(None, f"target node {target} lacks memory",
                            requested_mb, candidates, policy=active_policy)
        return Decision(tn.node_id, f"pinned to target node {target}",
                        requested_mb, candidates, policy=active_policy)

    eligible = [n for n in nodes
                if n.healthy and n.memory_schedulable_mb >= requested_mb]
    if not eligible:
        return Decision(None, "no healthy node has enough memory",
                        requested_mb, candidates, policy=active_policy)

    if active_policy == "first_fit":
        # first healthy node with sufficient memory
        selected_node = eligible[0]
        return Decision(selected_node.node_id, "first fit with sufficient memory",
                        requested_mb, candidates, policy=active_policy)
    elif active_policy == "best_fit":
        # smallest healthy node with sufficient memory (packs VMs tightly; node_id breaks ties)
        best = min(eligible, key=lambda n: (n.memory_schedulable_mb, n.node_id))
        return Decision(best.node_id, "smallest sufficient memory",
                        requested_mb, candidates, policy=active_policy)
    else:
        # memory_aware (default): most free memory wins; node_id breaks ties so the result is stable
        best = max(eligible, key=lambda n: (n.memory_schedulable_mb, n.node_id))
        return Decision(best.node_id, "highest available memory",
                        requested_mb, candidates, policy=active_policy)
