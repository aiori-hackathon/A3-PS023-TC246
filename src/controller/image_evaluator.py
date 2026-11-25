"""Evaluates per-node boot readiness status for catalog OS images.

Statuses per node:
- READY: Passing record exists in evidence/image_boot_matrix.json matching current kernel sha256.
- FAILED(reason): Failing record exists matching current kernel sha256.
- NOT_VERIFIED: Default when image file exists but no passing/failing record exists for current kernel.
- UNAVAILABLE(file missing): Master image file is missing on host.
"""
from pathlib import Path
import hashlib
import json
import os
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_kernel_sha256(kernel_path: Optional[str] = None) -> str:
    """Compute sha256 of the current active direct-boot kernel."""
    if not kernel_path:
        env_k = os.environ.get("PS023_KERNEL")
        if env_k:
            kernel_path = env_k
        else:
            k = REPO_ROOT / "lab" / "kernel" / "vmlinux.bin"
            if k.exists():
                kernel_path = str(k)
            else:
                knet = REPO_ROOT / "lab" / "kernel" / "vmlinux-net.bin"
                if knet.exists():
                    kernel_path = str(knet)
    if kernel_path and Path(kernel_path).exists():
        try:
            return hashlib.sha256(Path(kernel_path).read_bytes()).hexdigest()
        except Exception:
            return ""
    return ""


def load_boot_matrix(matrix_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load records from evidence/image_boot_matrix.json."""
    if not matrix_path:
        matrix_path = os.environ.get(
            "PS023_BOOT_MATRIX",
            str(REPO_ROOT / "evidence" / "image_boot_matrix.json")
        )
    p = Path(matrix_path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def evaluate_image_node_status(
    image: Dict[str, Any],
    matrix_records: Optional[List[Dict[str, Any]]] = None,
    current_kernel_sha256: Optional[str] = None,
    node_ids: Optional[List[str]] = None
) -> Dict[str, str]:
    """Calculate per-node status for an image.

    Returns dict mapping node_id -> status string:
      READY | FAILED(<reason>) | UNAVAILABLE(file missing) | NOT_VERIFIED
    """
    if node_ids is None:
        node_ids = ["node-a", "node-b"]

    img_path_str = image.get("path") or ""
    img_path = Path(img_path_str)
    # Check if master image file exists on host
    if not img_path.is_file():
        return {node: "UNAVAILABLE(file missing)" for node in node_ids}

    if matrix_records is None:
        matrix_records = load_boot_matrix()
    if current_kernel_sha256 is None:
        current_kernel_sha256 = get_kernel_sha256()

    node_statuses = {}
    for node in node_ids:
        # Find latest record for this image and node
        matching = [
            r for r in matrix_records
            if r.get("image") == image.get("id") and r.get("node") == node
        ]
        if not matching:
            node_statuses[node] = "NOT_VERIFIED"
            continue

        latest = matching[-1]
        record_ksha = latest.get("kernel_sha256")
        # Invalidate record if kernel has changed or kernel_sha256 missing
        if not current_kernel_sha256 or record_ksha != current_kernel_sha256:
            node_statuses[node] = "NOT_VERIFIED"
            continue

        verdict = str(latest.get("verdict", "")).strip().upper()
        if verdict == "PASS":
            node_statuses[node] = "READY"
        elif verdict == "UNSUPPORTED":
            reason = latest.get("reason") or "unsupported architecture"
            node_statuses[node] = f"UNSUPPORTED({reason})"
        elif verdict == "FAIL":
            reason = latest.get("reason") or "verification failed"
            node_statuses[node] = f"FAILED({reason})"
        else:
            node_statuses[node] = "NOT_VERIFIED"

    return node_statuses


def enrich_image_status(
    image: Dict[str, Any],
    matrix_records: Optional[List[Dict[str, Any]]] = None,
    current_kernel_sha256: Optional[str] = None,
    node_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Enrich an image dictionary with node_status, dynamic status, and recomputed kernel_compat."""
    img = dict(image)
    node_status = evaluate_image_node_status(
        img,
        matrix_records=matrix_records,
        current_kernel_sha256=current_kernel_sha256,
        node_ids=node_ids
    )
    img["node_status"] = node_status

    # Any image supported by our monolithic kernel (with built-in XFS & Btrfs) is COMPATIBLE
    img["kernel_compat"] = "COMPATIBLE"

    # Compute overall status for backwards compatibility
    all_unavailable = all(s.startswith("UNAVAILABLE") for s in node_status.values())
    any_ready = any(s == "READY" for s in node_status.values())
    any_unsupported = any(s.startswith("UNSUPPORTED") for s in node_status.values())
    any_failed = any(s.startswith("FAILED") for s in node_status.values())

    if all_unavailable:
        img["status"] = "UNAVAILABLE"
    elif any_ready:
        img["status"] = "READY"
    elif any_unsupported:
        img["status"] = "UNSUPPORTED"
    elif any_failed:
        img["status"] = "FAILED"
    else:
        img["status"] = "NOT_VERIFIED"

    # Human-readable badge text
    # e.g., "A: Ready / B: Failed" or "A: Not Verified / B: Not Verified"
    def format_badge(s: str) -> str:
        if s == "READY":
            return "Ready"
        if s.startswith("UNSUPPORTED"):
            return "Unsupported"
        if s.startswith("FAILED"):
            return "Failed"
        if s.startswith("UNAVAILABLE"):
            return "Unavailable"
        return "Not Verified"

    st_a = format_badge(node_status.get("node-a", "NOT_VERIFIED"))
    st_b = format_badge(node_status.get("node-b", "NOT_VERIFIED"))
    img["badge"] = f"A: {st_a} / B: {st_b}"

    return img
