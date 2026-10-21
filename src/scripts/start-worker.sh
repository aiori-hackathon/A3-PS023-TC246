#!/bin/bash
cd $HOME/worker
set -a; . $HOME/worker.env; set +a
pkill -f '[u]vicorn main:app' 2>/dev/null || true
sleep 1
setsid $HOME/venv/bin/uvicorn main:app --host 192.168.100.17 --port 8002 >> $HOME/worker.log 2>&1 < /dev/null &
sleep 3
curl -s http://192.168.100.17:8002/health; echo
tail -n 3 $HOME/worker.log
