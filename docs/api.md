# Controller API

Base URL: `http://127.0.0.1:8000`

Every route except `GET /health` needs the header
`Authorization: Bearer <token>`. A missing or wrong token returns `401`.

| Method | Path | Success | Notes |
|---|---|---|---|
| GET | `/health` | 200 | No token needed. |
| GET | `/nodes` | 200 | All nodes with status and schedulable memory. |
| GET | `/nodes/{node_id}` | 200 | `404` if unknown. |
| GET | `/nodes/{node_id}/resources` | 200 | Proxied from the worker; `503` if unreachable, `502` on a worker error. |
| POST | `/vms` | 201 | Create and start a VM (body below). |
| GET | `/vms` | 200 | List VMs. |
| GET | `/vms/{vm_id}` | 200 | `404` if unknown. |
| POST | `/vms/{vm_id}/start` | 200 | |
| POST | `/vms/{vm_id}/stop` | 200 | Escalating stop (can take up to about 75 s on a frozen VMM). |
| DELETE | `/vms/{vm_id}` | 204 | |
| GET | `/decisions?limit=10` | 200 | Latest placement decisions; limit is clamped to 1-100. |

## Create request

```json
{"name": "web01", "vcpus": 1, "memory_mb": 512, "disk_gb": 4}
```

* `name`: lowercase letters, digits and `-`, 1-31 characters, must start with
  a letter or digit.
* `vcpus`: 1-8. `memory_mb`: 128-8192. `disk_gb`: 1-50 (default 4).
* Anything else returns `422`.
* `vm_id` must look like `vm-` followed by 8 hex digits, otherwise `422`.

## Error codes

| Code | Meaning |
|---|---|
| 401 | Missing or invalid bearer token. |
| 404 | Unknown VM or node. |
| 409 | No node could take the VM. The body has `detail` and the full `decision`. |
| 422 | Request validation failed. |
| 502 | A worker answered with an error. |
| 503 | The node that holds the VM is unreachable. |

## VM states

`PENDING`, `RUNNING`, `STOPPED`, `UNKNOWN` (its node is unhealthy), `FAILED`.
