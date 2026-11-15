"""Prometheus text exposition format metrics generator for PS-023 Controller."""
import time
from typing import Optional
import database as db


def escape_label_value(val: str) -> str:
    """Escape label values according to Prometheus text format spec."""
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def format_prometheus_metric(name: str, value: float | int, labels: Optional[dict[str, str]] = None) -> str:
    if labels:
        label_str = ",".join(f'{k}="{escape_label_value(v)}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


def generate_prometheus_metrics(path: Optional[str] = None) -> str:
    """Generate Prometheus exposition text format using real cluster data from database.
    
    Resilient: Will not raise exceptions if a node is offline or DB tables are empty.
    """
    now = time.time()
    lines: list[str] = []

    # 1. Node metrics
    try:
        nodes = db.list_nodes(path)
    except Exception:
        nodes = []

    total_nodes = len(nodes)
    healthy_nodes = sum(1 for n in nodes if n.get("status") == "HEALTHY")

    lines.append("# HELP ps023_nodes_total Total number of registered cluster nodes")
    lines.append("# TYPE ps023_nodes_total gauge")
    lines.append(f"ps023_nodes_total {total_nodes}")

    lines.append("# HELP ps023_nodes_healthy Total number of healthy cluster nodes")
    lines.append("# TYPE ps023_nodes_healthy gauge")
    lines.append(f"ps023_nodes_healthy {healthy_nodes}")

    if nodes:
        lines.append("# HELP ps023_node_up Operational status of the node (1 = healthy, 0 = unhealthy/offline)")
        lines.append("# TYPE ps023_node_up gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            is_up = 1 if n.get("status") == "HEALTHY" else 0
            lines.append(format_prometheus_metric("ps023_node_up", is_up, {"node": nid}))

        lines.append("# HELP ps023_node_healthy Health state of the node (1 = HEALTHY, 0 = UNHEALTHY/UNKNOWN)")
        lines.append("# TYPE ps023_node_healthy gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            is_healthy = 1 if n.get("status") == "HEALTHY" else 0
            lines.append(format_prometheus_metric("ps023_node_healthy", is_healthy, {"node": nid}))

        lines.append("# HELP ps023_node_memory_schedulable_bytes Schedulable memory available on the node in bytes")
        lines.append("# TYPE ps023_node_memory_schedulable_bytes gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            sched_mb = n.get("memory_schedulable_mb", 0) or 0
            lines.append(format_prometheus_metric("ps023_node_memory_schedulable_bytes", sched_mb * 1024 * 1024, {"node": nid}))

        lines.append("# HELP ps023_node_memory_schedulable_mb Schedulable memory available on the node in megabytes")
        lines.append("# TYPE ps023_node_memory_schedulable_mb gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            sched_mb = n.get("memory_schedulable_mb", 0) or 0
            lines.append(format_prometheus_metric("ps023_node_memory_schedulable_mb", sched_mb, {"node": nid}))

        lines.append("# HELP ps023_node_memory_reserved_bytes Memory reserved for host OS / existing VMs in bytes")
        lines.append("# TYPE ps023_node_memory_reserved_bytes gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            total_mb = n.get("memory_total_mb", 0) or 0
            sched_mb = n.get("memory_schedulable_mb", 0) or 0
            reserved_mb = max(0, total_mb - sched_mb)
            lines.append(format_prometheus_metric("ps023_node_memory_reserved_bytes", reserved_mb * 1024 * 1024, {"node": nid}))

        lines.append("# HELP ps023_node_memory_reserved_mb Memory reserved for host OS / existing VMs in megabytes")
        lines.append("# TYPE ps023_node_memory_reserved_mb gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            total_mb = n.get("memory_total_mb", 0) or 0
            sched_mb = n.get("memory_schedulable_mb", 0) or 0
            reserved_mb = max(0, total_mb - sched_mb)
            lines.append(format_prometheus_metric("ps023_node_memory_reserved_mb", reserved_mb, {"node": nid}))

        lines.append("# HELP ps023_node_cpu_cores Total physical/logical CPU cores on the node")
        lines.append("# TYPE ps023_node_cpu_cores gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            cpus = n.get("cpu_total", 0) or 0
            lines.append(format_prometheus_metric("ps023_node_cpu_cores", cpus, {"node": nid}))

        lines.append("# HELP ps023_node_cpu_usage_percent CPU utilization percentage on the node")
        lines.append("# TYPE ps023_node_cpu_usage_percent gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            cpu_pct = float(n.get("cpu_percent", 0.0) or 0.0)
            lines.append(format_prometheus_metric("ps023_node_cpu_usage_percent", cpu_pct, {"node": nid}))

        lines.append("# HELP ps023_node_last_heartbeat_timestamp_seconds Unix timestamp of the latest node heartbeat")
        lines.append("# TYPE ps023_node_last_heartbeat_timestamp_seconds gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            hb = n.get("last_heartbeat")
            hb_val = float(hb) if hb is not None else 0.0
            lines.append(format_prometheus_metric("ps023_node_last_heartbeat_timestamp_seconds", hb_val, {"node": nid}))

        lines.append("# HELP ps023_node_heartbeat_age_seconds Seconds elapsed since the node's last heartbeat")
        lines.append("# TYPE ps023_node_heartbeat_age_seconds gauge")
        for n in nodes:
            nid = n.get("id", "unknown")
            hb = n.get("last_heartbeat")
            age = max(0.0, round(now - float(hb), 3)) if hb is not None else -1.0
            lines.append(format_prometheus_metric("ps023_node_heartbeat_age_seconds", age, {"node": nid}))

    # 2. VM metrics
    try:
        vms = db.list_vms(path)
    except Exception:
        vms = []

    lines.append("# HELP ps023_vms_total Total VMs partitioned by node, status, and HA mode")
    lines.append("# TYPE ps023_vms_total gauge")
    vm_counts: dict[tuple[str, str, str], int] = {}
    for v in vms:
        node_id = v.get("node_id", "unassigned")
        status = v.get("status", "UNKNOWN")
        ha_str = "true" if v.get("ha") else "false"
        key = (node_id, status, ha_str)
        vm_counts[key] = vm_counts.get(key, 0) + 1

    if not vm_counts:
        # Emit zero-samples for known nodes if empty
        for n in nodes:
            nid = n.get("id", "unknown")
            lines.append(format_prometheus_metric("ps023_vms_total", 0, {"node": nid, "status": "RUNNING", "ha": "false"}))
    else:
        for (node_id, status, ha_str), count in sorted(vm_counts.items()):
            lines.append(format_prometheus_metric("ps023_vms_total", count, {"node": node_id, "status": status, "ha": ha_str}))

    # 3. Decisions & Refusals (409)
    decisions_total = 0
    refusals_total = 0
    try:
        with db.connect(path) as c:
            r = c.execute("SELECT count(*) FROM decisions").fetchone()
            if r:
                decisions_total = r[0]
            r_ref = c.execute("SELECT count(*) FROM decisions WHERE selected IS NULL").fetchone()
            if r_ref:
                refusals_total = r_ref[0]
    except Exception:
        pass

    lines.append("# HELP ps023_decisions_total Total number of scheduler placement decisions recorded")
    lines.append("# TYPE ps023_decisions_total counter")
    lines.append(f"ps023_decisions_total {decisions_total}")

    lines.append("# HELP ps023_decision_refusals_total Total scheduler placement attempts resulting in capacity refusal (409)")
    lines.append("# TYPE ps023_decision_refusals_total counter")
    lines.append(f"ps023_decision_refusals_total {refusals_total}")

    # 4. Evacuations & Recovery Time
    evacuations_total = 0
    last_recovery_time_s = 0.0
    try:
        with db.connect(path) as c:
            r_evac = c.execute("SELECT count(*) FROM stale_vm_tombstones").fetchone()
            if r_evac:
                evacuations_total = r_evac[0]
            # Also check if any events recorded evacuations
            r_ev_events = c.execute("SELECT count(*) FROM events WHERE event_type LIKE '%evacuat%'").fetchone()
            if r_ev_events and r_ev_events[0] > evacuations_total:
                evacuations_total = r_ev_events[0]
            
            r_rec = c.execute("SELECT recovery_time_s FROM vms WHERE recovery_time_s IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
            if r_rec and r_rec[0] is not None:
                last_recovery_time_s = float(r_rec[0])
    except Exception:
        pass

    lines.append("# HELP ps023_evacuations_total Total number of VM auto-evacuation events recorded")
    lines.append("# TYPE ps023_evacuations_total counter")
    lines.append(f"ps023_evacuations_total {evacuations_total}")

    lines.append("# HELP ps023_last_recovery_time_seconds Duration in seconds of the most recent VM failover recovery")
    lines.append("# TYPE ps023_last_recovery_time_seconds gauge")
    lines.append(f"ps023_last_recovery_time_seconds {last_recovery_time_s:.3f}")

    return "\n".join(lines) + "\n"
