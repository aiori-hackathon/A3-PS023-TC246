"""SQLite storage for the controller. Standard library only."""
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get("PS023_DB", str(Path.home() / "ps023" / "controller.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    memory_total_mb INTEGER,
    memory_schedulable_mb INTEGER,
    cpu_total INTEGER,
    vms_running INTEGER,
    last_heartbeat REAL
);
CREATE TABLE IF NOT EXISTS vms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    node_id TEXT NOT NULL REFERENCES nodes(id),
    worker_vm_id TEXT,
    status TEXT NOT NULL,
    vcpus INTEGER NOT NULL,
    memory_mb INTEGER NOT NULL,
    disk_gb INTEGER NOT NULL,
    ip_address TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vm_id TEXT,
    at REAL NOT NULL,
    requested_mb INTEGER NOT NULL,
    selected TEXT,
    reason TEXT NOT NULL,
    candidates TEXT NOT NULL
);
"""

VM_FIELDS = {"name", "node_id", "worker_vm_id", "status", "vcpus",
             "memory_mb", "disk_gb", "ip_address"}
NODE_FIELDS = {"url", "status", "memory_total_mb", "memory_schedulable_mb",
               "cpu_total", "vms_running", "last_heartbeat"}


@contextmanager
def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path=None):
    with connect(path) as c:
        c.executescript(SCHEMA)


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


# ---------- nodes ----------
def upsert_node(node_id, url, path=None):
    with connect(path) as c:
        c.execute(
            "INSERT INTO nodes (id, url) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET url = excluded.url",
            (node_id, url),
        )


def update_node(node_id, path=None, **fields):
    bad = set(fields) - NODE_FIELDS
    if bad:
        raise ValueError(f"unknown node fields: {bad}")
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect(path) as c:
        c.execute(f"UPDATE nodes SET {sets} WHERE id = ?",
                  (*fields.values(), node_id))


def get_node(node_id, path=None):
    with connect(path) as c:
        r = c.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    return dict(r) if r else None


def list_nodes(path=None):
    with connect(path) as c:
        return _rows(c.execute("SELECT * FROM nodes ORDER BY id"))


# ---------- vms ----------
def add_vm(name, node_id, vcpus, memory_mb, disk_gb, status="PENDING", path=None):
    vm_id = "vm-" + uuid.uuid4().hex[:8]
    with connect(path) as c:
        c.execute(
            "INSERT INTO vms (id, name, node_id, status, vcpus, memory_mb, "
            "disk_gb, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vm_id, name, node_id, status, vcpus, memory_mb, disk_gb, time.time()),
        )
    return vm_id


def update_vm(vm_id, path=None, **fields):
    bad = set(fields) - VM_FIELDS
    if bad:
        raise ValueError(f"unknown vm fields: {bad}")
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect(path) as c:
        c.execute(f"UPDATE vms SET {sets} WHERE id = ?",
                  (*fields.values(), vm_id))


def get_vm(vm_id, path=None):
    with connect(path) as c:
        r = c.execute("SELECT * FROM vms WHERE id = ?", (vm_id,)).fetchone()
    return dict(r) if r else None


def list_vms(path=None):
    with connect(path) as c:
        return _rows(c.execute("SELECT * FROM vms ORDER BY created_at"))


def delete_vm(vm_id, path=None):
    with connect(path) as c:
        c.execute("DELETE FROM vms WHERE id = ?", (vm_id,))


# ---------- scheduler decisions ----------
def record_decision(decision, vm_id=None, path=None):
    with connect(path) as c:
        c.execute(
            "INSERT INTO decisions (vm_id, at, requested_mb, selected, reason, "
            "candidates) VALUES (?, ?, ?, ?, ?, ?)",
            (vm_id, time.time(), decision.requested_mb, decision.selected,
             decision.reason, json.dumps(decision.candidates)),
        )


def latest_decisions(limit=10, path=None):
    with connect(path) as c:
        rows = _rows(c.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)))
    for r in rows:
        r["candidates"] = json.loads(r["candidates"])
    return rows
