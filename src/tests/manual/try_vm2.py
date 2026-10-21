import socket
import time

from vm_manager import VMManager


def ssh_up(ip):
    try:
        with socket.create_connection((ip, 22), timeout=1):
            return True
    except OSError:
        return False


m = VMManager()
vm = m.create("web02", vcpus=1, memory_mb=1024, disk_gb=4)
print("created:", vm["id"], vm["ip"])
m.start(vm["id"])
t0 = time.time()
while time.time() - t0 < 120 and not ssh_up(vm["ip"]):
    time.sleep(1)
print(f"ssh port open after {time.time() - t0:.0f}s")

t1 = time.time()
print("stop via:", m.stop(vm["id"]))
print(f"stop took {time.time() - t1:.0f}s")
m.delete(vm["id"])
print("vms left:", len(m.list()))
