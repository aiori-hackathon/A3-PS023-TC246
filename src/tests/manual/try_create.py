import os
import sys
import tempfile
import time

import database as db
import vm_service as svc

path = os.path.join(tempfile.mkdtemp(), "t.db")
db.init_db(path)
db.upsert_node("node-a", "http://127.0.0.1:8001", path)
db.upsert_node("node-b", "http://127.0.0.1:8002", path)
mode = sys.argv[1] if len(sys.argv) > 1 else "lifecycle"


def show_decisions():
    for r in reversed(db.latest_decisions(5, path)):
        print("decision:", r["selected"], "|", r["reason"], "|",
              [(c["node_id"], c["available_mb"], c["verdict"])
               for c in r["candidates"]])


if mode == "nocapacity":
    try:
        svc.create_vm("huge", 1, 999999, 4, path)
    except svc.NoCapacity as e:
        print("NoCapacity:", e)
        show_decisions()
    sys.exit()

if mode == "failover":
    # node-b is dead but looks healthy and roomy, like in the 15 s window
    db.update_node("node-b", path, status="HEALTHY",
                   memory_schedulable_mb=99999, last_heartbeat=time.time())

vm = svc.create_vm("demo01", 1, 1024, 4, path)
print("created:", vm["id"], vm["node_id"], vm["status"], vm["ip_address"])
show_decisions()

if mode == "lifecycle":
    time.sleep(12)  # let the guest finish booting so the stop is graceful
    print("stop:", svc.stop_vm(vm["id"], path)["status"])
    print("start:", svc.start_vm(vm["id"], path)["status"])
    time.sleep(12)

svc.delete_vm(vm["id"], path)
print("deleted; vms in db:", len(db.list_vms(path)))
