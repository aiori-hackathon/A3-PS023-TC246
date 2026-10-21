import os
import tempfile

import database as db
from scheduler import NodeView, place

path = os.path.join(tempfile.mkdtemp(), "test.db")
db.init_db(path)

db.upsert_node("node-a", "http://127.0.0.1:8001", path)
db.upsert_node("node-b", "http://127.0.0.1:8002", path)
db.update_node("node-a", path, status="HEALTHY", memory_schedulable_mb=9000)
assert db.get_node("node-a", path)["status"] == "HEALTHY"
assert len(db.list_nodes(path)) == 2

vm = db.add_vm("web01", "node-a", 2, 1024, 4, path=path)
assert vm.startswith("vm-")
assert db.get_vm(vm, path)["status"] == "PENDING"
db.update_vm(vm, path, status="RUNNING", ip_address="192.168.100.10")
assert db.get_vm(vm, path)["status"] == "RUNNING"

# an unknown column must be rejected
try:
    db.update_vm(vm, path, bogus="x")
    raise SystemExit("FAIL: bogus field accepted")
except ValueError:
    pass

# a VM on a node that does not exist must be rejected (foreign key)
try:
    db.add_vm("ghost", "node-zzz", 1, 512, 4, path=path)
    raise SystemExit("FAIL: foreign key not enforced")
except Exception as e:
    assert "FOREIGN KEY" in str(e).upper(), e

d = place([NodeView("node-a", True, 9000), NodeView("node-b", True, 3000)], 2048)
db.record_decision(d, vm, path)
last = db.latest_decisions(1, path)[0]
assert last["selected"] == "node-a" and len(last["candidates"]) == 2

db.delete_vm(vm, path)
assert db.get_vm(vm, path) is None
print("all database tests passed")
