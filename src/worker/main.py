"""Worker: authenticated HTTP API in front of VMManager."""
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth import load_token, make_auth_dependency
from resource_monitor import get_resources
from vm_manager import VMError, VMManager

NODE_ID = os.environ.get("PS023_NODE_ID", "node-a")

app = FastAPI(title=f"PS-023 worker {NODE_ID}")
manager = VMManager()
require_token = make_auth_dependency(load_token())
auth = [Depends(require_token)]

# vm ids become file paths, so only accept the exact format we generate
VmId = Annotated[str, Path(pattern=r"^vm-[0-9a-f]{8}$")]


class CreateVM(BaseModel):
    # the name goes into cloud-init, so restrict it to a safe hostname
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,30}$")
    vcpus: int = Field(ge=1, le=8)
    memory_mb: int = Field(ge=128, le=8192)
    disk_gb: int = Field(default=4, ge=1, le=50)
    start: bool = True


@app.exception_handler(VMError)
def vm_error_handler(request, exc):
    code = 404 if str(exc).startswith("unknown vm") else 409
    return JSONResponse(status_code=code, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "node_id": NODE_ID}


@app.get("/resources", dependencies=auth)
def resources():
    return get_resources(NODE_ID, manager.list())


@app.get("/vms", dependencies=auth)
def list_vms():
    return manager.list()


@app.get("/vms/{vm_id}", dependencies=auth)
def get_vm(vm_id: VmId):
    return manager.get(vm_id)


@app.post("/vms", status_code=201, dependencies=auth)
def create_vm(req: CreateVM):
    res = get_resources(NODE_ID, manager.list())
    if req.memory_mb > res["memory_schedulable_mb"]:
        raise HTTPException(
            status_code=409,
            detail=(f"insufficient memory: requested {req.memory_mb} MB, "
                    f"schedulable {res['memory_schedulable_mb']} MB"),
        )
    meta = manager.create(req.name, req.vcpus, req.memory_mb, req.disk_gb)
    if req.start:
        try:
            manager.start(meta["id"])
        except Exception:
            manager.delete(meta["id"])  # never leave a half-made VM behind
            raise
    return manager.get(meta["id"])


@app.post("/vms/{vm_id}/start", dependencies=auth)
def start_vm(vm_id: VmId):
    manager.start(vm_id)
    return manager.get(vm_id)


@app.post("/vms/{vm_id}/stop", dependencies=auth)
def stop_vm(vm_id: VmId):
    how = manager.stop(vm_id)
    return {**manager.get(vm_id), "stopped_via": how}


@app.delete("/vms/{vm_id}", status_code=204, dependencies=auth)
def delete_vm(vm_id: VmId):
    manager.delete(vm_id)
