"""Thin client for the Cloud Hypervisor management API (one VMM per socket)."""
import httpx

API = "http://localhost/api/v1"


class VMMUnreachable(Exception):
    """Cannot connect to the API socket: the VMM is not running."""


class APIError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class CloudHypervisor:
    def __init__(self, socket_path, timeout=10.0):
        self.socket_path = socket_path
        self._client = httpx.Client(
            transport=httpx.HTTPTransport(uds=socket_path),
            base_url=API,
            timeout=timeout,
        )

    def _call(self, method, path, json=None):
        try:
            r = self._client.request(method, path, json=json)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise VMMUnreachable(f"cannot connect to {self.socket_path}") from e
        return r

    def _ok(self, method, path, json=None):
        r = self._call(method, path, json)
        if r.status_code >= 400:
            raise APIError(r.status_code, r.text)
        return r.json() if r.content else None

    def ping(self):
        return self._ok("GET", "/vmm.ping")

    def create(self, config):
        return self._ok("PUT", "/vm.create", config)

    def boot(self):
        return self._ok("PUT", "/vm.boot")

    def power_button(self):
        return self._ok("PUT", "/vm.power-button")

    def shutdown(self):
        return self._ok("PUT", "/vm.shutdown")

    def delete(self):
        return self._ok("PUT", "/vm.delete")

    def vmm_shutdown(self):
        return self._ok("PUT", "/vmm.shutdown")

    def counters(self):
        return self._ok("GET", "/vm.counters")

    def state(self):
        """One word: 'unreachable', 'not_created', or the VM state
        ('Created', 'Running', 'Shutdown', 'Paused')."""
        try:
            r = self._call("GET", "/vm.info")
        except VMMUnreachable:
            return "unreachable"
        if r.status_code == 404:
            return "not_created"
        if r.status_code >= 400:
            raise APIError(r.status_code, r.text)
        return r.json()["state"]
