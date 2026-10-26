"""Controller: authenticated REST API over the scheduler and the workers."""
import dataclasses
import os
import threading
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import database as db
import node_service as ns
import reconcile as rc
import vm_service as svc
from auth import load_api_token, make_auth_dependency
from worker_client import WorkerClient, WorkerError, WorkerUnreachable, token_for

POLL_INTERVAL_S = 5

require_token = make_auth_dependency(load_api_token())
auth = [Depends(require_token)]

VmId = Annotated[str, Path(pattern=r"^vm-[0-9a-f]{8}$")]
NodeId = Annotated[str, Path(pattern=r"^[a-z0-9-]{1,32}$")]

stop_event = threading.Event()


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


@app.post("/vms", status_code=201, dependencies=auth)
def create_vm(req: CreateVM):
    return svc.create_vm(req.name, req.vcpus, req.memory_mb, req.disk_gb)


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


from pathlib import Path  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

app.mount("/dashboard",
          StaticFiles(directory=Path(__file__).parent / "dashboard", html=True),
          name="dashboard")


from terminal import router as terminal_router  # noqa: E402

app.include_router(terminal_router)
