"""Controller -> worker HTTP client with bearer-token authentication."""
import os

import httpx


class WorkerUnreachable(Exception):
    """Could not talk to the worker (down, network failure, or timeout)."""


class WorkerError(Exception):
    """The worker answered with an HTTP error."""

    def __init__(self, status, detail):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def token_for(node_id):
    name = "PS023_TOKEN_" + node_id.upper().replace("-", "_")
    token = os.environ.get(name)
    if not token:
        raise RuntimeError(f"{name} is not set")
    return token


class WorkerClient:
    def __init__(self, node_id, url, token=None):
        self.node_id = node_id
        self._client = httpx.Client(
            base_url=url,
            headers={"Authorization": f"Bearer {token or token_for(node_id)}"},
            timeout=10.0,
        )

    def close(self):
        self._client.close()

    def _req(self, method, path, json=None, timeout=10.0):
        try:
            r = self._client.request(method, path, json=json, timeout=timeout)
        except httpx.TransportError as e:  # connect, timeout, protocol errors
            raise WorkerUnreachable(f"{self.node_id}: {e!r}") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise WorkerError(r.status_code, detail)
        return r.json() if r.content else None

    def health(self):
        return self._req("GET", "/health", timeout=3.0)

    def resources(self):
        return self._req("GET", "/resources", timeout=5.0)

    def list_vms(self):
        return self._req("GET", "/vms")

    def get_vm(self, worker_vm_id):
        return self._req("GET", f"/vms/{worker_vm_id}")

    def create_vm(self, name, vcpus, memory_mb, disk_gb, start=True):
        body = {"name": name, "vcpus": vcpus, "memory_mb": memory_mb,
                "disk_gb": disk_gb, "start": start}
        return self._req("POST", "/vms", json=body, timeout=60.0)

    def start_vm(self, worker_vm_id):
        return self._req("POST", f"/vms/{worker_vm_id}/start", timeout=30.0)

    def stop_vm(self, worker_vm_id):
        return self._req("POST", f"/vms/{worker_vm_id}/stop", timeout=100.0)

    def delete_vm(self, worker_vm_id):
        return self._req("DELETE", f"/vms/{worker_vm_id}", timeout=100.0)
