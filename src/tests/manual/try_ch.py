import os
from cloud_hypervisor import CloudHypervisor, VMMUnreachable

sock = os.path.expanduser("~/ps023/lab/sockets/vm1.sock")
ch = CloudHypervisor(sock)

print("state:", ch.state())
try:
    print("ping:", ch.ping())
except VMMUnreachable as e:
    print("ping: VMMUnreachable ->", e)
