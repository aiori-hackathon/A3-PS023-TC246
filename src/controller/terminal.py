"""Browser terminal: a WebSocket that relays text to an SSH session on a VM.

Protocol (all client messages are JSON text frames):
  1. hello:   {"token": "<API token>", "cols": 80, "rows": 24}
  2. input:   {"type": "input", "data": "ls\\r"}
  3. resize:  {"type": "resize", "cols": 100, "rows": 30}
The server sends the VM's terminal output as binary frames.

Close codes: 4400 bad hello, 4401 bad token, 4404 unknown or not-running VM,
4429 too many sessions, 4500 controller misconfigured, 4502 SSH failed.
"""
import asyncio
import hmac
import json
import os
import re

import asyncssh
from fastapi import APIRouter, WebSocket

import database as db
from auth import load_api_token

router = APIRouter()

VM_ID = re.compile(r"^vm-[0-9a-f]{8}$")
MAX_SESSIONS = 5
HELLO_TIMEOUT_S = 10
SSH_CONNECT_TIMEOUT_S = 10
_active = 0


def _dim(value, default):
    return value if isinstance(value, int) and 1 <= value <= 500 else default


@router.websocket("/vms/{vm_id}/terminal")
async def terminal(ws: WebSocket, vm_id: str):
    global _active
    await ws.accept()
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), HELLO_TIMEOUT_S))
        if not isinstance(hello, dict):
            raise ValueError("hello must be an object")
    except Exception:
        await ws.close(code=4400, reason="expected a JSON hello")
        return

    # authenticate before revealing anything about the VM
    supplied = str(hello.get("token", ""))
    if not hmac.compare_digest(supplied.encode(), load_api_token().encode()):
        await ws.close(code=4401, reason="invalid token")
        return

    vm = db.get_vm(vm_id) if VM_ID.fullmatch(vm_id) else None
    if vm is None or vm["status"] != "RUNNING" or not vm["ip_address"]:
        await ws.close(code=4404, reason="vm not found or not running")
        return

    password = os.environ.get("PS023_VM_PASSWORD", "")
    if not password:
        await ws.close(code=4500, reason="controller has no VM password")
        return
    if _active >= MAX_SESSIONS:
        await ws.close(code=4429, reason="too many terminal sessions")
        return

    _active += 1
    try:
        await _relay(ws, vm["ip_address"], password, hello)
    finally:
        _active -= 1


async def _relay(ws, ip, password, hello):
    user = os.environ.get("PS023_VM_USER", "rajyavardhan")
    try:
        # VM host keys change whenever a VM is recreated, and the VMs sit on a
        # private virtual network, so host keys are not checked.
        conn = await asyncssh.connect(
            ip, username=user, password=password, known_hosts=None,
            connect_timeout=SSH_CONNECT_TIMEOUT_S)
    except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
        await ws.close(code=4502, reason="ssh failed: " + type(e).__name__)
        return
    try:
        proc = await conn.create_process(
            term_type="xterm-256color",
            term_size=(_dim(hello.get("cols"), 80), _dim(hello.get("rows"), 24)),
            encoding=None)

        async def vm_to_browser():
            while True:
                data = await proc.stdout.read(4096)
                if not data:
                    return
                await ws.send_bytes(data)

        async def browser_to_vm():
            while True:
                try:
                    msg = json.loads(await ws.receive_text())
                except ValueError:
                    continue  # ignore malformed frames
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "input":
                    proc.stdin.write(str(msg.get("data", "")).encode())
                elif msg.get("type") == "resize":
                    proc.change_terminal_size(_dim(msg.get("cols"), 80),
                                              _dim(msg.get("rows"), 24))

        tasks = [asyncio.create_task(vm_to_browser()),
                 asyncio.create_task(browser_to_vm())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for t in done:
            t.exception()  # mark as retrieved (a browser disconnect lands here)
    finally:
        conn.close()
        try:
            await ws.close()
        except Exception:
            pass  # already closed by the browser
