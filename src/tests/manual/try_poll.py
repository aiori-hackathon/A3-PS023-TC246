import os
import time

import database as db
import node_service as ns

path = "/tmp/ps023-poll-test.db"
if os.path.exists(path):
    os.remove(path)
db.init_db(path)
db.upsert_node("node-a", "http://127.0.0.1:8001", path)
db.upsert_node("node-b", "http://127.0.0.1:8002", path)

for _ in range(30):
    ns.poll_all(path)
    row = [(n["id"], n["status"], n["memory_schedulable_mb"])
           for n in db.list_nodes(path)]
    print(time.strftime("%H:%M:%S"), row, flush=True)
    time.sleep(5)
