#!/bin/bash
# Inner network of node-b: bridge br-inner 10.77.0.1/24, TAP pool, NAT out via ens3.
set -e
ip link show br-inner >/dev/null 2>&1 || { sudo ip link add br-inner type bridge; sudo ip addr add 10.77.0.1/24 dev br-inner; }
sudo ip link set br-inner up
for n in 0 1 2 3; do
  ip link show tapvm$n >/dev/null 2>&1 || sudo ip tuntap add dev tapvm$n mode tap user $USER
  sudo ip link set tapvm$n master br-inner
  sudo ip link set tapvm$n up
done
sudo sysctl -qw net.ipv4.ip_forward=1
ip -br addr show br-inner
ip -br link show master br-inner
