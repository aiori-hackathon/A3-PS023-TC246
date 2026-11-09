#!/usr/bin/env bash
# ==============================================================================
# PS-023: WireGuard Tunnel Setup on Node B (AWS EC2)
# Generates Node B keypair, configures wg0 (10.100.0.2/24), enables wg-quick@wg0
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
  apt-get update -qq && apt-get install -y -qq wireguard
}

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

# Generate keys with strict umask 077 if not present
if [ ! -f "$PRIV_KEY" ]; then
  echo "Generating WireGuard keypair for Node B (AWS)..."
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

# Check if wg0.conf exists and already has laptop peer configured
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
AllowedIPs = 10.100.0.1/32
EOF

chmod 600 "$CONF_FILE"

echo "Enabling and starting wg-quick@wg0..."
systemctl enable wg-quick@wg0
# Start or reload wg0
if systemctl is-active --quiet wg-quick@wg0; then
  echo "Reloading WireGuard interface wg0..."
  systemctl restart wg-quick@wg0
else
  echo "Starting WireGuard interface wg0..."
  systemctl start wg-quick@wg0 || echo "Warning: wg-quick failed to start. Ensure peer public key is replaced first."
fi

echo
echo "======================================================================"
echo "Node B WireGuard Setup Complete!"
echo "Node B Public Key: $NODE_B_PUB"
echo
echo "Next Steps:"
echo "1. On Node A (laptop), run wg_setup_node_a.sh with:"
echo "   - Node B Public Key: $NODE_B_PUB"
echo "   - Node B Endpoint: <AWS_ELASTIC_IP>:51820"
echo "2. Edit $CONF_FILE and replace PLACEHOLDER_LAPTOP_PUBLIC_KEY with"
echo "   the public key from Node A."
echo "3. Run: sudo systemctl restart wg-quick@wg0"
echo "======================================================================"
