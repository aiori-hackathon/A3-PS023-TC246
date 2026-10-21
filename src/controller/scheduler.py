"""Memory-based VM placement. Pure logic: no network, no database."""
from dataclasses import dataclass, field


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


def place(nodes, requested_mb):
    candidates = []
    for n in nodes:
        if not n.healthy:
            verdict = "skipped: unhealthy"
        elif n.memory_schedulable_mb < requested_mb:
            verdict = "skipped: not enough memory"
        else:
            verdict = "eligible"
        candidates.append({
            "node_id": n.node_id,
            "healthy": n.healthy,
            "available_mb": n.memory_schedulable_mb,
            "verdict": verdict,
        })

    eligible = [n for n in nodes
                if n.healthy and n.memory_schedulable_mb >= requested_mb]
    if not eligible:
        return Decision(None, "no healthy node has enough memory",
                        requested_mb, candidates)

    # most free memory wins; node_id breaks ties so the result is stable
    best = max(eligible, key=lambda n: (n.memory_schedulable_mb, n.node_id))
    return Decision(best.node_id, "highest available memory",
                    requested_mb, candidates)
