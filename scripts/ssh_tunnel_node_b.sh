#!/usr/bin/env bash
AZURE_IP="${1:-<NODE_B_PUBLIC_IP>}"
while true; do
    ssh -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 \
        -o StrictHostKeyChecking=accept-new \
        -N -L 8012:127.0.0.1:8002 "ubuntu@${AZURE_IP}"
    sleep 2
done
