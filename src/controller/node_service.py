"""Node health: poll each worker and record the result."""
import os
import time

import database as db
from worker_client import WorkerClient, WorkerError, WorkerUnreachable

DEFAULT_UNHEALTHY_AFTER_S = 15.0


def unhealthy_threshold():
    try:
        return float(os.environ.get("PS023_UNHEALTHY_THRESHOLD_S", DEFAULT_UNHEALTHY_AFTER_S))
    except (ValueError, TypeError):
        return DEFAULT_UNHEALTHY_AFTER_S


UNHEALTHY_AFTER_S = unhealthy_threshold()


def health_status(last_heartbeat, now, threshold=None):
    """Pure rule, easy to test: no heartbeat, or too old, means UNHEALTHY."""
    if threshold is None:
        threshold = unhealthy_threshold()
    if last_heartbeat is None:
        return "UNHEALTHY"
    return "HEALTHY" if now - last_heartbeat <= threshold else "UNHEALTHY"


def poll_node(node, now=None, path=None):
    now = time.time() if now is None else now
    client = WorkerClient(node["id"], node["url"])  # a missing token raises
    try:
        res = client.resources()
    except (WorkerUnreachable, WorkerError):
        status = health_status(node["last_heartbeat"], now)
        db.update_node(node["id"], path, status=status)
        return status
    finally:
        client.close()
    db.update_node(
        node["id"], path,
        status="HEALTHY",
        memory_total_mb=res["memory_total_mb"],
        memory_schedulable_mb=res["memory_schedulable_mb"],
        cpu_total=res["cpu_total"],
        vms_running=res["vms_running"],
        last_heartbeat=now,
        cgroups_enabled=1 if res.get("cgroups_enabled") else 0,
    )
    return "HEALTHY"


def poll_all(path=None):
    return {n["id"]: poll_node(n, path=path) for n in db.list_nodes(path)}
