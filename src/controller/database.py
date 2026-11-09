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
    last_heartbeat REAL,
    cgroups_enabled INTEGER NOT NULL DEFAULT 0
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
    created_at REAL NOT NULL,
    ha INTEGER NOT NULL DEFAULT 0,
    image TEXT DEFAULT 'ubuntu-24-04',
    user_data TEXT,
    tags TEXT DEFAULT '[]',
    evacuation_started_at REAL,
    evacuation_retries INTEGER DEFAULT 0,
    evacuation_error TEXT,
    recovery_time_s REAL,
    cgroups INTEGER NOT NULL DEFAULT 0,
    cgroup_limits TEXT
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
CREATE TABLE IF NOT EXISTS stale_vm_tombstones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    worker_vm_id TEXT NOT NULL,
    vm_name TEXT NOT NULL,
    evacuated_at REAL NOT NULL,
    fenced_at REAL
);
"""

VM_FIELDS = {
    "name", "node_id", "worker_vm_id", "status", "vcpus",
    "memory_mb", "disk_gb", "ip_address", "ha", "image",
    "user_data", "tags", "evacuation_started_at",
    "evacuation_retries", "evacuation_error", "recovery_time_s",
    "cgroups", "cgroup_limits"
}
NODE_FIELDS = {"url", "status", "memory_total_mb", "memory_schedulable_mb",
               "cpu_total", "vms_running", "last_heartbeat", "cgroups_enabled"}


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
        # Safe, idempotent migration for existing databases
        cursor = c.cursor()
        node_cols = {col[1] for col in cursor.execute("PRAGMA table_info(nodes)").fetchall()}
        if "cgroups_enabled" not in node_cols:
            cursor.execute("ALTER TABLE nodes ADD COLUMN cgroups_enabled INTEGER NOT NULL DEFAULT 0")

        vm_cols = {col[1] for col in cursor.execute("PRAGMA table_info(vms)").fetchall()}
        new_cols = [
            ("ha", "INTEGER NOT NULL DEFAULT 0"),
            ("image", "TEXT DEFAULT 'ubuntu-24-04'"),
            ("user_data", "TEXT"),
            ("tags", "TEXT DEFAULT '[]'"),
            ("evacuation_started_at", "REAL"),
            ("evacuation_retries", "INTEGER DEFAULT 0"),
            ("evacuation_error", "TEXT"),
            ("recovery_time_s", "REAL"),
            ("cgroups", "INTEGER NOT NULL DEFAULT 0"),
            ("cgroup_limits", "TEXT"),
        ]
        for col_name, col_def in new_cols:
            if col_name not in vm_cols:
                cursor.execute(f"ALTER TABLE vms ADD COLUMN {col_name} {col_def}")


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def _format_node(node):
    if node is None:
        return None
    d = dict(node)
    if "cgroups_enabled" in d:
        d["cgroups_enabled"] = bool(d["cgroups_enabled"])
    return d


def _format_vm(vm):
    if vm is None:
        return None
    d = dict(vm)
    if "ha" in d:
        d["ha"] = bool(d["ha"])
    if "cgroups" in d:
        d["cgroups"] = bool(d["cgroups"])
    if "cgroup_limits" in d and isinstance(d["cgroup_limits"], str):
        try:
            d["cgroup_limits"] = json.loads(d["cgroup_limits"])
        except Exception:
            pass
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            pass
    return d


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
    return _format_node(r)


def list_nodes(path=None):
    with connect(path) as c:
        return [_format_node(r) for r in c.execute("SELECT * FROM nodes ORDER BY id").fetchall()]


# ---------- vms ----------
def add_vm(name, node_id, vcpus, memory_mb, disk_gb, status="PENDING", path=None,
           ha=False, image="ubuntu-24-04", user_data=None, tags=None):
    vm_id = "vm-" + uuid.uuid4().hex[:8]
    tags_json = json.dumps(tags or [])
    with connect(path) as c:
        c.execute(
            "INSERT INTO vms (id, name, node_id, status, vcpus, memory_mb, "
            "disk_gb, created_at, ha, image, user_data, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (vm_id, name, node_id, status, vcpus, memory_mb, disk_gb,
             time.time(), 1 if ha else 0, image, user_data, tags_json),
        )
    return vm_id


def update_vm(vm_id, path=None, **fields):
    bad = set(fields) - VM_FIELDS
    if bad:
        raise ValueError(f"unknown vm fields: {bad}")
    if not fields:
        return
    if "ha" in fields:
        fields["ha"] = 1 if fields["ha"] else 0
    if "tags" in fields and isinstance(fields["tags"], (list, dict)):
        fields["tags"] = json.dumps(fields["tags"])
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect(path) as c:
        c.execute(f"UPDATE vms SET {sets} WHERE id = ?",
                  (*fields.values(), vm_id))


def get_vm(vm_id, path=None):
    with connect(path) as c:
        r = c.execute("SELECT * FROM vms WHERE id = ?", (vm_id,)).fetchone()
    return _format_vm(r)


def list_vms(path=None):
    with connect(path) as c:
        rows = _rows(c.execute("SELECT * FROM vms ORDER BY created_at"))
    return [_format_vm(r) for r in rows]


def delete_vm(vm_id, path=None):
    with connect(path) as c:
        c.execute("DELETE FROM vms WHERE id = ?", (vm_id,))


# ---------- tombstones & fencing ----------
def add_tombstone(node_id, worker_vm_id, vm_name, path=None):
    with connect(path) as c:
        c.execute(
            "INSERT INTO stale_vm_tombstones (node_id, worker_vm_id, vm_name, evacuated_at) "
            "VALUES (?, ?, ?, ?)",
            (node_id, worker_vm_id, vm_name, time.time()),
        )


def get_pending_tombstones(node_id, path=None):
    with connect(path) as c:
        return _rows(c.execute(
            "SELECT * FROM stale_vm_tombstones WHERE node_id = ? AND fenced_at IS NULL",
            (node_id,)
        ))


def mark_tombstone_fenced(tombstone_id, path=None):
    with connect(path) as c:
        c.execute(
            "UPDATE stale_vm_tombstones SET fenced_at = ? WHERE id = ?",
            (time.time(), tombstone_id),
        )


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
