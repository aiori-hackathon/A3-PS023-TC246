# Dashboard and VM terminal

The controller serves a single-page dashboard at
`http://127.0.0.1:8000/dashboard/` (keep the trailing slash). It calls the same
authenticated API as any other client; it has no privileges of its own.

## Using it

1. Open the page and paste the API token into the box at the top, then press
   **Connect**. The token is kept only for the current browser tab
   (`sessionStorage`) and is never written into the page or the repository.
2. The page refreshes every 5 s.

| Section | What it shows | API used |
|---|---|---|
| Nodes | Status, schedulable memory out of total, CPUs, running VMs, last heartbeat. | `GET /nodes` |
| Create a VM | Name, vCPUs, memory, disk. Shows the controller's error text if it refuses. | `POST /vms` |
| VMs | Status, node, resources and IP for each VM, with Start, Stop, Delete and Terminal buttons. | `GET /vms`, `POST /vms/{id}/start`, `POST /vms/{id}/stop`, `DELETE /vms/{id}` |
| Latest placement decisions | The last five decisions with every candidate node and why it was eligible, skipped or refused. | `GET /decisions?limit=5` |

Stop can take up to about 75 s when a VM does not respond, so the Stop button
stays disabled until the call returns.

All values from the API are written into the page as text (never as HTML).

## Terminal

The **Terminal** button appears for a VM that is `RUNNING` and has an IP. It
opens a shell on the VM inside the page (xterm.js, served from
`dashboard/vendor/`, so no internet access is needed).

```
browser  --WebSocket-->  controller  --SSH-->  VM
```

Endpoint: `WS /vms/{vm_id}/terminal`

Messages from the browser are JSON text frames:

| Frame | Meaning |
|---|---|
| `{"token": "<API token>", "cols": 80, "rows": 24}` | First message. Must carry the API token. |
| `{"type": "input", "data": "ls\r"}` | Keystrokes. |
| `{"type": "resize", "cols": 100, "rows": 30}` | The terminal was resized. |

The controller sends the VM's terminal output as binary frames.

| Close code | Reason |
|---|---|
| 4400 | The first message was not valid JSON. |
| 4401 | Wrong or missing token. |
| 4404 | Unknown VM id, VM not found, or VM not `RUNNING`. |
| 4429 | More than 5 terminal sessions are open. |
| 4500 | The controller has no VM password configured. |
| 4502 | The SSH connection failed. |

How it is protected:

* The token is checked before anything about the VM is revealed. Browsers
  cannot send an `Authorization` header on a WebSocket, so the token travels in
  the first message instead.
* The controller connects only to the IP stored in its own database for a
  `RUNNING` VM; the browser never supplies an address.
* The VM login password (`PS023_VM_PASSWORD`) stays on the controller and is
  never sent to the browser.
* At most 5 sessions can be open at once.

Limits to be aware of (also listed in the report):

* Anyone holding the API token can open a shell on any running VM. The token is
  the only protection, so use a long random one.
* SSH host keys are not checked, because VMs are re-created often and sit on a
  private virtual network.
* Traffic between the browser and the controller is plain HTTP unless TLS is
  put in front of it, so use it on localhost or a private link only.
* The controller logs in with one shared account (`PS023_VM_USER`, default
  `rajyavardhan`).

## Files

* `src/controller/terminal.py`: the WebSocket route.
* `src/controller/dashboard/index.html`: the page.
* `src/controller/dashboard/vendor/`: xterm.js 5.3.0 and xterm-addon-fit 0.8.0
  (MIT licence, from the npm packages `xterm` and `xterm-addon-fit`).
* `src/controller/test_terminal.py`: automated tests for the route (see
  `testing.md`).
