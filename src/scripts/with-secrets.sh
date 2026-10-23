#!/bin/bash
# Usage: bash ~/ps023/with-secrets.sh bash ~/ps023/controller/try_api.sh
set -a
. "$HOME/ps023/secrets.env"
set +a
export SSHPASS="$PS023_VM_PASSWORD"
exec "$@"
