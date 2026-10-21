import subprocess
import time

from vm_manager import VMManager

m = VMManager()
vm = m.create("web01", vcpus=2, memory_mb=1024, disk_gb=4)
print("created:", vm["id"], vm["ip"], vm["tap"])

m.start(vm["id"])
t0 = time.time()
print("status:", m.status(vm["id"]))

while time.time() - t0 < 90:
    ok = subprocess.run(["ping", "-c1", "-W1", vm["ip"]],
                        capture_output=True).returncode == 0
    if ok:
        print(f"VM answered ping after {time.time() - t0:.0f}s")
        break
else:
    print("no ping within 90s")

print("list:", [(v["name"], v["status"]) for v in m.list()])
print("stop via:", m.stop(vm["id"]))
print("status:", m.status(vm["id"]))
m.delete(vm["id"])
print("deleted; vms left:", len(m.list()))
