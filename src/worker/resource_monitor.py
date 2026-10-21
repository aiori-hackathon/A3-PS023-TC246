"""Host resource report for the controller's scheduler."""
import psutil

# Memory kept back for the host itself, so a placement never starves it.
HOST_RESERVE_MB = 1024


def get_resources(node_id, vms):
    """vms: list of VM dicts from VMManager.list()."""
    mem = psutil.virtual_memory()
    total_mb = mem.total // (1024 * 1024)
    available_mb = mem.available // (1024 * 1024)

    running = [v for v in vms if v["status"] == "running"]
    committed_mb = sum(v["memory_mb"] for v in running)
    committed_vcpus = sum(v["vcpus"] for v in running)

    return {
        "node_id": node_id,
        "cpu_total": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_committed_vcpus": committed_vcpus,
        "memory_total_mb": total_mb,
        "memory_available_mb": available_mb,
        "memory_committed_mb": committed_mb,
        "memory_schedulable_mb": max(0, available_mb - HOST_RESERVE_MB),
        "vms_total": len(vms),
        "vms_running": len(running),
    }
