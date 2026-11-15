"""Controller: authenticated REST API over the scheduler and the workers."""
import dataclasses
import hashlib
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path as FastPath, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database as db
import metrics as prom_metrics
import node_service as ns
import reconcile as rc
import vm_service as svc
from auth import load_api_token, make_auth_dependency
from scheduler import place
from terminal import router as terminal_router
from worker_client import WorkerClient, WorkerError, WorkerUnreachable, token_for

POLL_INTERVAL_S = 5

require_token = make_auth_dependency(load_api_token())
auth = [Depends(require_token)]

VmId = Annotated[str, FastPath(pattern=r"^vm-[0-9a-f]{8}$")]
NodeId = Annotated[str, FastPath(pattern=r"^[a-z0-9-]{1,32}$")]
ImageId = Annotated[str, FastPath(pattern=r"^[a-z0-9-]{2,40}$")]

stop_event = threading.Event()

def get_image_root() -> Path:
    raw = os.environ.get("PS023_IMAGE_ROOT") or os.environ.get("PS023_IMAGES_DIR") or str(Path.home() / "ps023" / "images")
    return Path(raw).expanduser().resolve()


IMAGES_DIR = get_image_root()


def parse_nodes():
    nodes = {}
    for item in os.environ.get("PS023_NODES", "").split(","):
        item = item.strip()
        if not item:
            continue
        node_id, _, url = item.partition("=")
        if not node_id or not url:
            raise RuntimeError(f"bad PS023_NODES entry: {item!r} (want id=url)")
        nodes[node_id] = url
    if not nodes:
        raise RuntimeError("PS023_NODES must list at least one node")
    return nodes


def poll_loop():
    while not stop_event.is_set():
        try:
            ns.poll_all()
            rc.reconcile()
        except Exception as e:  # keep polling no matter what
            print("poll error:", repr(e), flush=True)
        stop_event.wait(POLL_INTERVAL_S)


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    for node_id, url in parse_nodes().items():
        token_for(node_id)  # fail now if a token is missing
        db.upsert_node(node_id, url)
    try:
        ns.poll_all()
    except Exception as e:
        print("initial poll error:", repr(e), flush=True)
    threading.Thread(target=poll_loop, daemon=True).start()
    yield
    stop_event.set()


app = FastAPI(title="PS-023 controller", lifespan=lifespan)


class CreateVM(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,30}$")
    vcpus: int = Field(ge=1, le=8)
    memory_mb: int = Field(ge=128, le=8192)
    disk_gb: int = Field(default=4, ge=1, le=50)
    ha: bool = False
    image: str = "ubuntu-24-04"
    user_data: str | None = None
    tags: list[str] = Field(default_factory=list)
    target_node: str | None = None
    policy: str | None = None


class SchedulerPreviewRequest(BaseModel):
    memory_mb: int = Field(ge=128, le=8192)
    vcpus: int = Field(default=1, ge=1, le=8)
    target_node: str | None = None
    policy: str | None = None


class ImportImageRequest(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    name: str = Field(min_length=2, max_length=100)
    distro: str = Field(min_length=2, max_length=50)
    version: str = Field(default="1.0", min_length=1, max_length=50)
    path: str
    format: str = "raw"
    expected_sha256: str | None = None


@app.exception_handler(svc.NotFound)
def on_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": f"unknown vm {exc}"})


@app.exception_handler(svc.NoCapacity)
def on_no_capacity(request, exc):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "decision": dataclasses.asdict(exc.decision)},
    )


@app.exception_handler(svc.NodeUnavailable)
def on_node_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(svc.WorkerRejected)
def on_worker_rejected(request, exc):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# ---------- Redirects ----------
@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/dashboard/", status_code=307)


@app.get("/terminals", include_in_schema=False)
def terminals_redirect():
    return RedirectResponse(url="/dashboard/#terminals", status_code=307)


@app.get("/vms/{vm_id}/terminal-page", include_in_schema=False)
def vm_terminal_redirect(vm_id: VmId):
    return RedirectResponse(url=f"/dashboard/#terminals?vm_id={vm_id}", status_code=307)


# ---------- Health & Nodes ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/nodes", dependencies=auth)
def list_nodes():
    return db.list_nodes()


@app.get("/nodes/{node_id}", dependencies=auth)
def get_node(node_id: NodeId):
    node = db.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"unknown node {node_id}")
    return node


@app.get("/nodes/{node_id}/resources", dependencies=auth)
def node_resources(node_id: NodeId):
    node = db.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"unknown node {node_id}")
    client = WorkerClient(node["id"], node["url"])
    try:
        return client.resources()
    except WorkerUnreachable:
        raise HTTPException(status_code=503, detail=f"{node_id} is unreachable")
    except WorkerError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        client.close()


@app.get("/nodes/{node_id}/metrics", dependencies=auth)
def node_metrics(node_id: NodeId, since: float | None = None, limit: int = 120):
    node = db.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"unknown node {node_id}")
    clamped_limit = max(1, min(limit, 720))
    metrics = db.get_node_metrics(node_id, since=since, limit=clamped_limit)
    return {
        "node_id": node_id,
        "metrics": metrics,
        "sample_count": len(metrics),
        "last_sample_time": metrics[-1]["timestamp"] if metrics else None,
    }


@app.get("/cluster/metrics", dependencies=auth)
def cluster_metrics():
    nodes = db.list_nodes()
    total_nodes = len(nodes)
    healthy_nodes = sum(1 for n in nodes if n["status"] == "HEALTHY")

    total_cpu_cores = sum(n.get("cpu_total", 0) or 0 for n in nodes if n["status"] == "HEALTHY")
    cpu_weighted_sum = sum((n.get("cpu_percent", 0.0) or 0.0) * (n.get("cpu_total", 0) or 0) for n in nodes if n["status"] == "HEALTHY")
    avg_cpu_percent = round(cpu_weighted_sum / total_cpu_cores, 2) if total_cpu_cores > 0 else 0.0

    total_mem_mb = sum(n.get("memory_total_mb", 0) or 0 for n in nodes if n["status"] == "HEALTHY")
    avail_mem_mb = sum(n.get("memory_available_mb", 0) or 0 for n in nodes if n["status"] == "HEALTHY")
    used_mem_mb = sum(n.get("memory_used_mb", 0) or 0 for n in nodes if n["status"] == "HEALTHY")
    sched_mem_mb = sum(n.get("memory_schedulable_mb", 0) or 0 for n in nodes if n["status"] == "HEALTHY")
    mem_percent = round((used_mem_mb / total_mem_mb * 100), 2) if total_mem_mb > 0 else 0.0

    return {
        "total_nodes": total_nodes,
        "healthy_nodes": healthy_nodes,
        "total_cpu_cores": total_cpu_cores,
        "cluster_cpu_percent": avg_cpu_percent,
        "total_memory_mb": total_mem_mb,
        "used_memory_mb": used_mem_mb,
        "available_memory_mb": avail_mem_mb,
        "schedulable_memory_mb": sched_mem_mb,
        "cluster_memory_percent": mem_percent,
        "timestamp": time.time(),
    }


@app.get("/metrics", dependencies=auth, response_class=Response)
def get_prometheus_metrics():
    """Prometheus exposition format cluster metrics endpoint.
    
    Exposes real cluster node, memory, VM, decision refusal, and failover recovery metrics.
    Authentication: Requires valid Bearer token, matching other controller endpoints.
    """
    content = prom_metrics.generate_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


# ---------- VMs ----------
@app.post("/vms", status_code=201, dependencies=auth)
def create_vm(req: CreateVM):
    if req.image:
        img = db.get_image(req.image)
        if not img:
            raise HTTPException(status_code=422, detail=f"unknown image '{req.image}'")

    target = req.target_node
    if target and target != "auto":
        known = {n["id"] for n in db.list_nodes()}
        if target not in known:
            raise HTTPException(status_code=422, detail=f"unknown target_node '{target}'")

    kwargs = {
        "name": req.name,
        "vcpus": req.vcpus,
        "memory_mb": req.memory_mb,
        "disk_gb": req.disk_gb,
        "ha": req.ha,
        "image": req.image,
        "user_data": req.user_data,
        "tags": req.tags,
        "target_node": target,
    }
    if req.policy is not None:
        kwargs["policy"] = req.policy

    return svc.create_vm(**kwargs)


@app.get("/vms", dependencies=auth)
def list_vms():
    return svc.list_vms()


@app.get("/vms/{vm_id}", dependencies=auth)
def get_vm(vm_id: VmId):
    return svc.get_vm(vm_id)


@app.post("/vms/{vm_id}/start", dependencies=auth)
def start_vm(vm_id: VmId):
    return svc.start_vm(vm_id)


@app.post("/vms/{vm_id}/stop", dependencies=auth)
def stop_vm(vm_id: VmId):
    return svc.stop_vm(vm_id)


@app.delete("/vms/{vm_id}", status_code=204, dependencies=auth)
def delete_vm(vm_id: VmId):
    svc.delete_vm(vm_id)


@app.get("/decisions", dependencies=auth)
def decisions(limit: int = 10):
    return db.latest_decisions(max(1, min(limit, 100)))


# ---------- Scheduler Preview ----------
@app.get("/scheduler/preview", dependencies=auth)
def scheduler_preview_get(
    memory_mb: int = 512,
    vcpus: int = 1,
    target_node: str | None = None,
    policy: str | None = None,
):
    return scheduler_preview(
        SchedulerPreviewRequest(
            memory_mb=memory_mb,
            vcpus=vcpus,
            target_node=target_node,
            policy=policy,
        )
    )


@app.post("/scheduler/preview", dependencies=auth)
def scheduler_preview(req: SchedulerPreviewRequest):
    views = svc.node_views()
    all_nodes = {n["id"]: n for n in db.list_nodes()}

    reserved = {}
    for vm in db.list_vms():
        if vm["status"] in ("PENDING", "RUNNING", "UNKNOWN", "EVACUATING"):
            reserved[vm["node_id"]] = reserved.get(vm["node_id"], 0) + vm["memory_mb"]

    candidates_info = []
    for n in views:
        node_meta = all_nodes.get(n.node_id, {})
        tot = node_meta.get("memory_total_mb", 0) or 0
        sched = node_meta.get("memory_schedulable_mb", 0) or 0
        resv = reserved.get(n.node_id, 0)
        avail = max(0, sched - resv)
        accommodate = n.healthy and avail >= req.memory_mb
        candidates_info.append({
            "node_id": n.node_id,
            "healthy": n.healthy,
            "memory_total_mb": tot,
            "memory_schedulable_mb": sched,
            "memory_reserved_mb": resv,
            "memory_available_mb": avail,
            "estimated_remaining_mb": max(0, avail - req.memory_mb) if accommodate else avail,
            "can_accommodate": accommodate,
            "vms_running": n.vms_running,
        })

    target = req.target_node if (req.target_node and req.target_node != "auto") else None
    if target and target not in all_nodes:
        raise HTTPException(status_code=422, detail=f"unknown target_node '{target}'")

    decision = place(views, req.memory_mb, target_node=target, policy=req.policy)

    policy_choices = {}
    for pol in ("memory_aware", "first_fit", "best_fit"):
        d_pol = place(views, req.memory_mb, target_node=target, policy=pol)
        policy_choices[pol] = {
            "selected": d_pol.selected,
            "reason": d_pol.reason,
            "policy": pol,
        }

    return {
        "requested_mb": req.memory_mb,
        "requested_vcpus": req.vcpus,
        "policy": decision.policy,
        "recommended_node": decision.selected,
        "reason": decision.reason,
        "can_accommodate": decision.selected is not None,
        "nodes": candidates_info,
        "policy_choices": policy_choices,
    }


# ---------- Images ----------
@app.get("/images", dependencies=auth)
def list_images():
    return db.list_images()


@app.get("/images/{image_id}", dependencies=auth)
def get_image(image_id: ImageId):
    img = db.get_image(image_id)
    if not img:
        raise HTTPException(status_code=404, detail=f"unknown image {image_id}")
    return img


@app.post("/images/import", status_code=201, dependencies=auth)
def import_image(req: ImportImageRequest):
    # Security: reject path traversal sequences immediately
    if ".." in req.path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed ('..')")

    raw_path = Path(req.path).expanduser()
    if raw_path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks are not allowed for image paths")

    img_path = raw_path.resolve()
    if img_path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks are not allowed for image paths")

    # Restrict to configured images root (expanduser() and resolve() called BEFORE the check)
    image_root = get_image_root()
    image_root.mkdir(parents=True, exist_ok=True)
    try:
        img_path.relative_to(image_root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Image path must reside inside configured images directory ({image_root})"
        )

    if not img_path.exists() or not img_path.is_file():
        raise HTTPException(status_code=400, detail=f"File not found or not a regular file: {req.path}")

    if req.format.lower() != "raw":
        raise HTTPException(status_code=400, detail="Only RAW disk images are supported by Cloud Hypervisor direct kernel boot")

    size_bytes = img_path.stat().st_size
    if size_bytes < 100 * 1024 * 1024 and not os.environ.get("PS023_ALLOW_SMALL_IMAGES"):
        raise HTTPException(status_code=400, detail="Image size is suspiciously small for a bootable OS image (<100MB)")

    # Compute SHA-256 hash (never store size:<bytes> or VERIFIED without hash)
    try:
        h = hashlib.sha256()
        with img_path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        raw_hash = h.hexdigest().lower()
        checksum = f"sha256:{raw_hash}"

        if req.expected_sha256:
            clean_expected = req.expected_sha256.strip().lower()
            if clean_expected.startswith("sha256:"):
                clean_expected = clean_expected[7:]
            verification_status = "VERIFIED" if raw_hash == clean_expected else "UNVERIFIED"
        else:
            verification_status = "UNVERIFIED"
    except Exception:
        checksum = None
        verification_status = "UNVERIFIED"

    db.upsert_image(
        image_id=req.id,
        name=req.name,
        distro=req.distro,
        version=req.version,
        arch="x86_64",
        format="raw",
        path_img=str(img_path),
        disk_size_bytes=size_bytes,
        status="AVAILABLE",
        verification_status=verification_status,
        checksum=checksum,
    )
    db.record_event("IMAGE_IMPORTED", f"Imported OS image '{req.name}' ({req.id}) from {img_path}",
                    details={"image_id": req.id, "path": str(img_path), "size": size_bytes})
    return db.get_image(req.id)


@app.post("/images/validate/{image_id}", dependencies=auth)
def validate_image(image_id: ImageId):
    img = db.get_image(image_id)
    if not img:
        raise HTTPException(status_code=404, detail=f"unknown image {image_id}")
    p = Path(img["path"]) if img.get("path") else None
    if not p or not p.exists():
        db.upsert_image(
            image_id=img["id"], name=img["name"], distro=img["distro"], version=img["version"],
            arch=img["arch"], format=img["format"], path_img=img.get("path"), disk_size_bytes=None,
            status="MISSING", verification_status="FAILED", checksum=img.get("checksum"),
            download_url=img.get("download_url")
        )
        return {"id": image_id, "valid": False, "status": "MISSING", "error": "File does not exist on disk"}

    size = p.stat().st_size
    db.upsert_image(
        image_id=img["id"], name=img["name"], distro=img["distro"], version=img["version"],
        arch=img["arch"], format=img["format"], path_img=str(p), disk_size_bytes=size,
        status="AVAILABLE", verification_status="VERIFIED", checksum=img.get("checksum"),
        download_url=img.get("download_url")
    )
    return {"id": image_id, "valid": True, "status": "AVAILABLE", "size_bytes": size}


@app.delete("/images/{image_id}", status_code=204, dependencies=auth)
def delete_image(image_id: ImageId):
    try:
        db.delete_image(image_id)
        db.record_event("IMAGE_DELETED", f"Unregistered OS image '{image_id}'", details={"image_id": image_id})
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---------- Events ----------
@app.get("/events", dependencies=auth)
def list_events(limit: int = 50, event_type: str | None = None, level: str | None = None):
    return db.latest_events(limit=max(1, min(limit, 200)), event_type=event_type, level=level)


# ---------- Mounts & Routers ----------
app.mount("/dashboard",
          StaticFiles(directory=Path(__file__).parent / "dashboard", html=True),
          name="dashboard")

app.include_router(terminal_router)
