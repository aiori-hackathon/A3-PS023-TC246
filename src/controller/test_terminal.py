import asyncio
import os

import pytest

TOKEN = "test-token-0123456789abcdef"
os.environ["PS023_API_TOKEN"] = TOKEN  # same value as the other API tests

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

import terminal  # noqa: E402

VM = "vm-12345678"
RUNNING = {"id": VM, "status": "RUNNING", "ip_address": "192.168.100.10"}

app = FastAPI()
app.include_router(terminal.router)
client = TestClient(app)


class FakeStdin:
    def __init__(self, proc):
        self.proc = proc

    def write(self, data):
        self.proc.written.append(data)
        self.proc.got_input.set()


class FakeStdout:
    def __init__(self, proc):
        self.proc = proc
        self.first = True

    async def read(self, n):
        if self.first:
            self.first = False
            return b"hello from vm\r\n"
        await self.proc.got_input.wait()  # then end the session
        return b""


class FakeProc:
    def __init__(self, size):
        self.size = size
        self.written = []
        self.got_input = asyncio.Event()
        self.stdin = FakeStdin(self)
        self.stdout = FakeStdout(self)

    def change_terminal_size(self, cols, rows):
        self.size = (cols, rows)


class FakeConn:
    procs = []
    closed = 0

    async def create_process(self, **kw):
        p = FakeProc(kw["term_size"])
        FakeConn.procs.append(p)
        return p

    def close(self):
        FakeConn.closed += 1


@pytest.fixture(autouse=True)
def env(monkeypatch):
    FakeConn.procs, FakeConn.closed = [], 0
    monkeypatch.setenv("PS023_VM_PASSWORD", "pw-for-tests")
    monkeypatch.setattr(terminal.db, "get_vm", lambda vm_id: RUNNING)
    monkeypatch.setattr(terminal, "_active", 0)

    async def connect(ip, **kw):
        assert ip == "192.168.100.10" and kw["username"] and kw["password"] == "pw-for-tests"
        return FakeConn()
    monkeypatch.setattr(terminal.asyncssh, "connect", connect)


def close_code(path, first_message):
    with pytest.raises(WebSocketDisconnect) as e:
        with client.websocket_connect(path) as ws:
            ws.send_text(first_message)
            ws.receive_text()
    return e.value.code


def hello(**over):
    import json
    d = {"token": TOKEN, "cols": 100, "rows": 30}
    d.update(over)
    return json.dumps(d)


def test_wrong_token_rejected():
    assert close_code(f"/vms/{VM}/terminal", hello(token="nope")) == 4401
    assert FakeConn.procs == []  # never reached SSH


def test_missing_token_rejected():
    assert close_code(f"/vms/{VM}/terminal", "{}") == 4401


def test_bad_hello_rejected():
    assert close_code(f"/vms/{VM}/terminal", "not json") == 4400


def test_bad_vm_id_rejected():
    assert close_code("/vms/vm-xxxxxxxx/terminal", hello()) == 4404


def test_unknown_vm_rejected(monkeypatch):
    monkeypatch.setattr(terminal.db, "get_vm", lambda vm_id: None)
    assert close_code(f"/vms/{VM}/terminal", hello()) == 4404


def test_stopped_vm_rejected(monkeypatch):
    monkeypatch.setattr(terminal.db, "get_vm",
                        lambda vm_id: {**RUNNING, "status": "STOPPED"})
    assert close_code(f"/vms/{VM}/terminal", hello()) == 4404


def test_missing_vm_password_is_reported(monkeypatch):
    monkeypatch.delenv("PS023_VM_PASSWORD")
    assert close_code(f"/vms/{VM}/terminal", hello()) == 4500


def test_session_limit(monkeypatch):
    monkeypatch.setattr(terminal, "_active", terminal.MAX_SESSIONS)
    assert close_code(f"/vms/{VM}/terminal", hello()) == 4429


def test_ssh_failure_is_reported(monkeypatch):
    async def boom(ip, **kw):
        raise OSError("no route")
    monkeypatch.setattr(terminal.asyncssh, "connect", boom)
    assert close_code(f"/vms/{VM}/terminal", hello()) == 4502


def test_output_input_and_cleanup():
    with client.websocket_connect(f"/vms/{VM}/terminal") as ws:
        ws.send_text(hello())
        assert ws.receive_bytes() == b"hello from vm\r\n"
        ws.send_text('{"type": "resize", "cols": 120, "rows": 40}')
        ws.send_text('{"type": "input", "data": "ls\\r"}')
        with pytest.raises(WebSocketDisconnect):
            ws.receive_bytes()  # the fake VM ends the session after input
    proc = FakeConn.procs[0]
    assert proc.written == [b"ls\r"]
    assert proc.size == (120, 40)
    assert FakeConn.closed == 1
    assert terminal._active == 0
