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
    candidates TEXT NOT NULL,
    policy TEXT DEFAULT 'memory_aware'
);
CREATE TABLE IF NOT EXISTS stale_vm_tombstones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    worker_vm_id TEXT NOT NULL,
    vm_name TEXT NOT NULL,
    evacuated_at REAL NOT NULL,
    fenced_at REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at REAL NOT NULL,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    details TEXT,
    source TEXT DEFAULT 'controller'
);
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    distro TEXT NOT NULL,
    version TEXT NOT NULL,
    arch TEXT NOT NULL DEFAULT 'x86_64',
    format TEXT NOT NULL DEFAULT 'raw',
    path TEXT,
    disk_size_bytes INTEGER,
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    verification_status TEXT DEFAULT 'VERIFIED',
    checksum TEXT,
    download_url TEXT,
    created_at REAL NOT NULL,
    kernel_compat TEXT DEFAULT 'COMPATIBLE',
    notes TEXT,
    kernel_path TEXT,
    initrd_path TEXT,
    cmdline TEXT DEFAULT 'console=ttyS0 root=/dev/vda1'
);
CREATE TABLE IF NOT EXISTS node_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES nodes(id),
    timestamp REAL NOT NULL,
    cpu_percent REAL NOT NULL,
    memory_used_mb INTEGER NOT NULL,
    memory_total_mb INTEGER NOT NULL,
    memory_available_mb INTEGER NOT NULL,
    memory_percent REAL NOT NULL,
    disk_used_mb INTEGER,
    disk_total_mb INTEGER,
    disk_percent REAL,
    network_rx_kbps REAL,
    network_tx_kbps REAL,
    vms_running INTEGER NOT NULL
);
"""

DEFAULT_IMAGES = [
    {
        "id": "ubuntu-24-04",
        "name": "Ubuntu Server 24.04 LTS",
        "distro": "Ubuntu",
        "version": "24.04 LTS (Noble Numbat)",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "lab" / "images" / "ubuntu-noble.raw"),
        "disk_size_bytes": 3758096384,
        "status": "AVAILABLE",
        "verification_status": "COMPUTED_LOCALLY",
        "checksum": "sha256:78c756f1272375e29b03ff62225c9a51e640c55059e745b4a3eca3a1efbdebf0",
        "download_url": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
        "kernel_compat": "COMPATIBLE",
        "notes": "Ubuntu noble raw disk image. Checksum computed locally, not compared to upstream. Bootable out of the box via direct kernel boot.",
    },
    {
        "id": "debian-12",
        "name": "Debian 12 Bookworm",
        "distro": "Debian",
        "version": "12 (Bookworm)",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "debian-12.raw"),
        "disk_size_bytes": 3221225472,
        "status": "AVAILABLE",
        "verification_status": "COMPUTED_LOCALLY",
        "checksum": "sha256:97df81890768b28518dd236b937f5b59342d6212b48179d8a8b9230c27c6eb27",
        "download_url": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.raw",
        "kernel_compat": "COMPATIBLE",
        "notes": "Debian 12 genericcloud raw image. Checksum computed locally, not compared to upstream. Status: not boot-tested.",
    },
    {
        "id": "fedora-40",
        "name": "Fedora Server 40",
        "distro": "Fedora",
        "version": "40 Server",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "fedora-40.raw"),
        "disk_size_bytes": None,
        "status": "NOT_DOWNLOADED",
        "verification_status": "UNVERIFIED",
        "checksum": "no checksum",
        "download_url": "https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/40/Cloud/x86_64/images/Fedora-Cloud-Base-Generic.x86_64-40-1.14.qcow2",
        "kernel_compat": "REQUIRES_CONVERSION",
        "notes": "Fedora Cloud Base image (not downloaded, no checksum). Must be converted from QCOW2 to RAW format. Status: not boot-tested.",
    },
    {
        "id": "rocky-9",
        "name": "Rocky Linux 9",
        "distro": "Rocky Linux",
        "version": "9.4 (Blue Onyx)",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "rocky-9.raw"),
        "disk_size_bytes": None,
        "status": "NOT_DOWNLOADED",
        "verification_status": "UNVERIFIED",
        "checksum": "no checksum",
        "download_url": "https://download.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2",
        "kernel_compat": "REQUIRES_CONVERSION",
        "notes": "Rocky Linux 9 GenericCloud image (not downloaded, no checksum). Requires QCOW2 to RAW conversion. Status: not boot-tested.",
    },
    {
        "id": "almalinux-9",
        "name": "AlmaLinux 9",
        "distro": "AlmaLinux",
        "version": "9.4 (Seafoam Ocelot)",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "almalinux-9.raw"),
        "disk_size_bytes": None,
        "status": "NOT_DOWNLOADED",
        "verification_status": "UNVERIFIED",
        "checksum": "no checksum",
        "download_url": "https://repo.almalinux.org/almalinux/9/cloud/x86_64/images/AlmaLinux-9-GenericCloud-latest.x86_64.qcow2",
        "kernel_compat": "REQUIRES_CONVERSION",
        "notes": "AlmaLinux 9 GenericCloud image (not downloaded, no checksum). Requires QCOW2 to RAW conversion. Status: not boot-tested.",
    },
    {
        "id": "opensuse-15-6",
        "name": "openSUSE Leap 15.6",
        "distro": "openSUSE",
        "version": "15.6",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "opensuse-15-6.raw"),
        "disk_size_bytes": None,
        "status": "NOT_DOWNLOADED",
        "verification_status": "UNVERIFIED",
        "checksum": "no checksum",
        "download_url": "https://download.opensuse.org/distribution/leap/15.6/appliances/openSUSE-Leap-15.6-Minimal-VM.x86_64-Cloud.qcow2",
        "kernel_compat": "REQUIRES_CONVERSION",
        "notes": "openSUSE Leap 15.6 Cloud appliance (not downloaded, no checksum). Requires QCOW2 to RAW conversion. Status: not boot-tested.",
    },
    {
        "id": "arch-linux",
        "name": "Arch Linux",
        "distro": "Arch Linux",
        "version": "Rolling (Latest)",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "arch-linux.raw"),
        "disk_size_bytes": 2147483648,
        "status": "INCOMPATIBLE_KERNEL",
        "verification_status": "COMPUTED_LOCALLY",
        "checksum": "sha256:c7d27449e8fa2732a97fcf5c4e56f35762c230873b00328384c1226b2fa30bc9",
        "download_url": "https://geo.mirror.pkgbuild.com/images/latest/Arch-Linux-x86_64-cloudimg.qcow2",
        "kernel_compat": "INCOMPATIBLE_BTRFS",
        "notes": "Arch Linux raw disk image. Checksum computed locally, not compared to upstream. Status: not boot-tested. Direct-boot kernel requires ext4 (btrfs incompatible).",
    },
    {
        "id": "alpine-3-20",
        "name": "Alpine Linux 3.20 (virt)",
        "distro": "Alpine",
        "version": "3.20.3",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "alpine-3-20.raw"),
        "disk_size_bytes": 134217728,
        "status": "NOT_DOWNLOADED",
        "verification_status": "OFFICIAL_UPSTREAM",
        "checksum": "sha256:81df854fbd7327d293c726b1eeeb82061d3bc8f5a86a6f77eea720f6be372261",
        "download_url": "https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-virt-3.20.3-x86_64.iso",
        "kernel_compat": "COMPATIBLE",
        "kernel_path": "/boot/vmlinuz-virt",
        "initrd_path": "/boot/initramfs-virt",
        "cmdline": "console=ttyS0 root=/dev/vda1 modules=ext4,virtio_pci,virtio_net",
        "notes": "Official Alpine Linux 3.20 virt image (not downloaded). Upstream official release SHA-256 from https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-virt-3.20.3-x86_64.iso.sha256. Status: not boot-tested.",
    },
    {
        "id": "cirros-0-6-2",
        "name": "CirrOS 0.6.2",
        "distro": "CirrOS",
        "version": "0.6.2",
        "arch": "x86_64",
        "format": "raw",
        "path": str(Path.home() / "ps023" / "images" / "cirros-0.6.2-x86_64-disk.img"),
        "disk_size_bytes": 16777216,
        "status": "NOT_DOWNLOADED",
        "verification_status": "OFFICIAL_MD5_UNOFFICIAL_SHA256",
        "checksum": "sha256:07e44a73e54c94d988028515403c1ed762055e01b83a767edf3c2b387f78ce00",
        "download_url": "https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img",
        "kernel_compat": "COMPATIBLE",
        "kernel_path": "/boot/vmlinuz",
        "initrd_path": "/boot/initrd.img",
        "cmdline": "console=ttyS0 root=/dev/vda1 ro",
        "notes": "CirrOS 0.6.2 minimal image (not downloaded). Official host publishes MD5SUMS only (c8fc807773e5354afe61636071771906); SHA-256 is unofficial/locally computed. Status: not boot-tested.",
    },
]

VM_FIELDS = {
    "name", "node_id", "worker_vm_id", "status", "vcpus",
    "memory_mb", "disk_gb", "ip_address", "ha", "image",
    "user_data", "tags", "evacuation_started_at",
    "evacuation_retries", "evacuation_error", "recovery_time_s",
    "cgroups", "cgroup_limits"
}
NODE_FIELDS = {"url", "status", "memory_total_mb", "memory_schedulable_mb",
               "cpu_total", "vms_running", "last_heartbeat", "cgroups_enabled"}


def _enforce_db_permissions(db_file):
    p = Path(db_file)
    if p.exists():
        try:
            p.chmod(0o600)
        except OSError:
            pass
    for ext in ("-wal", "-shm", "-journal"):
        aux = p.with_name(p.name + ext)
        if aux.exists():
            try:
                aux.chmod(0o600)
            except OSError:
                pass


@contextmanager
def connect(path=None):
    db_file = path or DB_PATH
    conn = sqlite3.connect(db_file, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    _enforce_db_permissions(db_file)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        _enforce_db_permissions(db_file)


def init_db(path=None):
    db_file = path or DB_PATH
    _enforce_db_permissions(db_file)
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

        dec_cols = {col[1] for col in cursor.execute("PRAGMA table_info(decisions)").fetchall()}
        if "policy" not in dec_cols:
            cursor.execute("ALTER TABLE decisions ADD COLUMN policy TEXT DEFAULT 'memory_aware'")

        img_cols = {col[1] for col in cursor.execute("PRAGMA table_info(images)").fetchall()}
        new_img_cols = [
            ("kernel_path", "TEXT"),
            ("initrd_path", "TEXT"),
            ("cmdline", "TEXT DEFAULT 'console=ttyS0 root=/dev/vda1'"),
        ]
        for col_name, col_def in new_img_cols:
            if col_name not in img_cols:
                cursor.execute(f"ALTER TABLE images ADD COLUMN {col_name} {col_def}")

        for img in DEFAULT_IMAGES:
            existing = cursor.execute("SELECT 1 FROM images WHERE id = ?", (img["id"],)).fetchone()
            if not existing:
                cursor.execute(
                    "INSERT INTO images (id, name, distro, version, arch, format, path, "
                    "disk_size_bytes, status, verification_status, checksum, download_url, "
                    "created_at, kernel_compat, notes, kernel_path, initrd_path, cmdline) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (img["id"], img["name"], img["distro"], img["version"],
                     img.get("arch", "x86_64"), img.get("format", "raw"), img.get("path"),
                     img.get("disk_size_bytes"), img.get("status", "AVAILABLE"),
                     img.get("verification_status", "VERIFIED"), img.get("checksum"),
                     img.get("download_url"), time.time(),
                     img.get("kernel_compat", "COMPATIBLE"), img.get("notes"),
                     img.get("kernel_path"), img.get("initrd_path"),
                     img.get("cmdline", "console=ttyS0 root=/dev/vda1"))
                )


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
    policy = getattr(decision, "policy", "memory_aware") or "memory_aware"
    with connect(path) as c:
        c.execute(
            "INSERT INTO decisions (vm_id, at, requested_mb, selected, reason, "
            "candidates, policy) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (vm_id, time.time(), decision.requested_mb, decision.selected,
             decision.reason, json.dumps(decision.candidates), policy),
        )


def latest_decisions(limit=10, path=None):
    with connect(path) as c:
        rows = _rows(c.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)))
    for r in rows:
        r["candidates"] = json.loads(r["candidates"])
        r.setdefault("policy", "memory_aware")
    return rows


# ---------- events ----------
def record_event(event_type, message, level="INFO", details=None, source="controller", path=None):
    details_str = json.dumps(details) if isinstance(details, (dict, list)) else (str(details) if details is not None else None)
    with connect(path) as c:
        c.execute(
            "INSERT INTO events (at, event_type, level, message, details, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), event_type, level, message, details_str, source),
        )


def latest_events(limit=50, event_type=None, level=None, path=None):
    query = "SELECT * FROM events"
    params = []
    conditions = []
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if level:
        conditions.append("level = ?")
        params.append(level)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY at DESC, id DESC LIMIT ?"
    params.append(limit)

    with connect(path) as c:
        rows = _rows(c.execute(query, params))
    for r in rows:
        if r.get("details"):
            try:
                r["details"] = json.loads(r["details"])
            except Exception:
                pass
    return rows


# ---------- images ----------
def list_images(path=None):
    with connect(path) as c:
        return _rows(c.execute("SELECT * FROM images ORDER BY id"))


def get_image(image_id, path=None):
    with connect(path) as c:
        r = c.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    return dict(r) if r else None


def upsert_image(image_id, name, distro, version="1.0", arch="x86_64",
                 format="raw", path_img=None, disk_size_bytes=None,
                 status="AVAILABLE", verification_status="VERIFIED",
                 checksum=None, download_url=None, kernel_compat="COMPATIBLE",
                 notes=None, kernel_path=None, initrd_path=None,
                 cmdline="console=ttyS0 root=/dev/vda1", path=None):
    with connect(path) as c:
        c.execute(
            "INSERT INTO images (id, name, distro, version, arch, format, path, "
            "disk_size_bytes, status, verification_status, checksum, download_url, "
            "created_at, kernel_compat, notes, kernel_path, initrd_path, cmdline) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, distro=excluded.distro, version=excluded.version, "
            "arch=excluded.arch, format=excluded.format, path=excluded.path, "
            "disk_size_bytes=excluded.disk_size_bytes, status=excluded.status, "
            "verification_status=excluded.verification_status, checksum=excluded.checksum, "
            "download_url=excluded.download_url, kernel_compat=excluded.kernel_compat, "
            "notes=excluded.notes, kernel_path=excluded.kernel_path, "
            "initrd_path=excluded.initrd_path, cmdline=excluded.cmdline",
            (image_id, name, distro, version, arch, format, path_img,
             disk_size_bytes, status, verification_status, checksum,
             download_url, time.time(), kernel_compat, notes,
             kernel_path, initrd_path, cmdline),
        )


def delete_image(image_id, path=None):
    with connect(path) as c:
        in_use = c.execute("SELECT count(*) FROM vms WHERE image = ?", (image_id,)).fetchone()[0]
        if in_use > 0:
            raise ValueError(f"Image '{image_id}' is in use by VM(s) and cannot be deleted")
        r = c.execute("DELETE FROM images WHERE id = ?", (image_id,))
        if r.rowcount == 0:
            raise KeyError(f"Image '{image_id}' not found")


# ---------- node metrics ----------
def record_node_metrics(node_id, cpu_percent, memory_used_mb, memory_total_mb,
                        memory_available_mb, memory_percent, timestamp=None,
                        disk_used_mb=None, disk_total_mb=None, disk_percent=None,
                        network_rx_kbps=None, network_tx_kbps=None, vms_running=0,
                        path=None):
    ts = timestamp if timestamp is not None else time.time()
    with connect(path) as c:
        c.execute(
            "INSERT INTO node_metrics (node_id, timestamp, cpu_percent, memory_used_mb, "
            "memory_total_mb, memory_available_mb, memory_percent, disk_used_mb, "
            "disk_total_mb, disk_percent, network_rx_kbps, network_tx_kbps, vms_running) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (node_id, ts, cpu_percent, memory_used_mb, memory_total_mb,
             memory_available_mb, memory_percent, disk_used_mb, disk_total_mb,
             disk_percent, network_rx_kbps, network_tx_kbps, vms_running),
        )


def get_node_metrics(node_id, since=None, limit=120, path=None):
    query = "SELECT * FROM node_metrics WHERE node_id = ?"
    params = [node_id]
    if since is not None:
        query += " AND timestamp >= ?"
        params.append(since)
    query += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)
    with connect(path) as c:
        return _rows(c.execute(query, params))
