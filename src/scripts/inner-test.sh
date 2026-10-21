#!/bin/bash
D=$HOME/nested
OLD=$(pgrep -f '[c]loud-hypervisor' | tr '\n' ',' | sed 's/,$//')
if [ -n "$OLD" ]; then
  echo "--- already running in node-b:"
  ps -o pid,etime,stat,args -p "$OLD" | cut -c1-160
  pkill -f '[c]loud-hypervisor'
  sleep 3
fi
rm -f $D/inner.sock $D/inner.sock.lock $D/inner-serial.log
[ -f $D/inner-test.raw ] || cp $D/images/ubuntu-noble.raw $D/inner-test.raw

setsid cloud-hypervisor --api-socket path=$D/inner.sock --cpus boot=1 --memory size=512M \
  --kernel $D/kernel/vmlinux.bin \
  --disk path=$D/inner-test.raw,image_type=raw \
  --cmdline "console=ttyS0 root=/dev/vda1 rw" \
  --serial file=$D/inner-serial.log --console off \
  > $D/inner-vmm.log 2>&1 < /dev/null &

for i in $(seq 1 240); do
  grep -q 'login:' $D/inner-serial.log 2>/dev/null && { echo "RESULT: inner VM reached a login prompt after ${i}s"; break; }
  sleep 1
done
echo "--- last serial lines:";  tail -n 4 $D/inner-serial.log 2>/dev/null
echo "--- vmm log:";            tail -n 4 $D/inner-vmm.log
echo "--- processes:";          pgrep -fa '[c]loud-hypervisor' | cut -c1-120
pkill -f '[c]loud-hypervisor'
sleep 2
pgrep -f '[c]loud-hypervisor' > /dev/null && echo "WARNING: still running" || echo "inner VM stopped"

