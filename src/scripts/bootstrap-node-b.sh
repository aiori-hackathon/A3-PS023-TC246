#!/bin/bash
set -e
rm -f $HOME/nested/inner-test.raw $HOME/nested/inner*.sock* $HOME/nested/inner-*.log
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3-pip mtools dosfstools iproute2 iputils-ping
python3 -m venv $HOME/venv
$HOME/venv/bin/pip install -q fastapi uvicorn httpx psutil
$HOME/venv/bin/python -c "import fastapi, uvicorn, httpx, psutil; print('deps OK')"
which mkfs.vfat mcopy ip ping
df -h / | tail -n 1
