#!/bin/bash
D=$HOME/ps023/outer
if pgrep -f "api-socket path=$D/outer.sock" > /dev/null; then
  echo "node-b VMM already running"; exit 0
fi
ip link show tapvm7 > /dev/null 2>&1 || { echo "tapvm7 missing: run the network setup first"; exit 1; }
rm -f $D/outer.sock $D/outer.sock.lock
setsid cloud-hypervisor \
  --api-socket path=$D/outer.sock \
  --cpus boot=4,nested=on \
  --memory size=4G \
  --kernel $HOME/ps023/lab/kernel/vmlinux.bin \
  --disk path=$D/disk.raw,image_type=raw \
  --disk path=$D/seed.img,image_type=raw,readonly=on \
  --net tap=tapvm7,mac=12:34:56:78:90:17 \
  --cmdline "console=ttyS0 root=/dev/vda1 rw" \
  --serial file=$D/serial.log --console off \
  >> $D/vmm.log 2>&1 < /dev/null &
echo "started, pid $!"
for i in $(seq 1 90); do
  (echo > /dev/tcp/192.168.100.17/22) 2>/dev/null && { echo "ssh port open after ${i}s"; exit 0; }
  sleep 1
done
echo "ssh not up after 90 s; see $D/serial.log and $D/vmm.log"
