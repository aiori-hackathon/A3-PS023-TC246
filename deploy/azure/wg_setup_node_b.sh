#!/usr/bin/env bash
# ==============================================================================
# PS-023: WireGuard Tunnel Setup on Node B (Microsoft Azure VM)
# Generates Node B keypair, configures wg0 (10.100.0.2/24), enables wg-quick@wg0
# Safe and idempotent.
# ==============================================================================
set -euo pipefail

WG_DIR="/etc/wireguard"
CONF_FILE="$WG_DIR/wg0.conf"
PRIV_KEY="$WG_DIR/private.key"
PUB_KEY="$WG_DIR/public.key"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: Please run as root or with sudo." >&2
  exit 1
fi

command -v wg >/dev/null 2>&1 || {
  echo "WireGuard not found. Installing wireguard..."
  apt-get update -qq && apt-get install -y -qq wireguard wireguard-tools
}

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

# Generate keys with strict umask 077 if not present
if [ ! -f "$PRIV_KEY" ]; then
  echo "Generating WireGuard keypair for Node B (Azure VM)..."
  (
    umask 077
    wg genkey | tee "$PRIV_KEY" | wg pubkey > "$PUB_KEY"
  )
  chmod 600 "$PRIV_KEY"
  chmod 644 "$PUB_KEY"
else
  echo "WireGuard keypair already exists at $PRIV_KEY."
fi

NODE_B_PRIV=$(cat "$PRIV_KEY")
NODE_B_PUB=$(cat "$PUB_KEY")

if [ -f "$CONF_FILE" ]; then
  echo "Backing up existing $CONF_FILE to $CONF_FILE.bak..."
  cp "$CONF_FILE" "$CONF_FILE.bak"
fi

cat > "$CONF_FILE" << EOF
[Interface]
# Node B Tunnel IP
Address = 10.100.0.2/24
ListenPort = 51820
PrivateKey = $NODE_B_PRIV

[Peer]
# Node A (Laptop Controller)
# Replace PLACEHOLDER_LAPTOP_PUBLIC_KEY with the output of wg_setup_node_a.sh
PublicKey = PLACEHOLDER_LAPTOP_PUBLIC_KEY
AllowedIPs = 10.100.0.1/32, 192.168.100.0/24
EOF

chmod 600 "$CONF_FILE"

echo "Enabling and starting wg-quick@wg0..."
systemctl enable wg-quick@wg0
if systemctl is-active --quiet wg-quick@wg0; then
  echo "Reloading WireGuard interface wg0..."
  systemctl restart wg-quick@wg0
else
  echo "Starting WireGuard interface wg0..."
  systemctl start wg-quick@wg0 || echo "Notice: wg-quick will fully establish once peer public key is set."
fi

echo
echo "======================================================================"
echo "Azure Node B WireGuard Setup Complete!"
echo "Node B Public Key: $NODE_B_PUB"
echo
echo "Next Steps:"
echo "1. On Node A (laptop), run wg_setup_node_a.sh with:"
echo "   - Node B Public Key: $NODE_B_PUB"
echo "   - Node B Endpoint:   <AZURE_PUBLIC_IP>:51820"
echo "2. Edit $CONF_FILE on this Azure VM:"
echo "   - Replace PLACEHOLDER_LAPTOP_PUBLIC_KEY with Node A's public key"
echo "3. Restart WireGuard: sudo systemctl restart wg-quick@wg0"
echo "======================================================================"
