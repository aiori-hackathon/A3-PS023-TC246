#!/usr/bin/env bash
# ==============================================================================
# PS-023: WireGuard Tunnel Setup on Node A (Laptop Controller) for Azure Node B
# Configures wg0 (10.100.0.1/24) pointing to Node B (Azure VM Endpoint)
# Safe and idempotent.
# ==============================================================================
set -euo pipefail

WG_DIR="/etc/wireguard"
CONF_FILE="$WG_DIR/wg0.conf"
PRIV_KEY="$WG_DIR/node_a_private.key"
PUB_KEY="$WG_DIR/node_a_public.key"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: Please run as root or with sudo." >&2
  exit 1
fi

command -v wg >/dev/null 2>&1 || {
  echo "WireGuard not installed. Installing wireguard-tools..."
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y wireguard-tools
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y -qq wireguard
  fi
}

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

# Generate keys with strict umask 077 if not present
if [ ! -f "$PRIV_KEY" ]; then
  echo "Generating WireGuard keypair for Node A (Laptop)..."
  (
    umask 077
    wg genkey | tee "$PRIV_KEY" | wg pubkey > "$PUB_KEY"
  )
  chmod 600 "$PRIV_KEY"
  chmod 644 "$PUB_KEY"
else
  echo "WireGuard keypair already exists at $PRIV_KEY."
fi

NODE_A_PRIV=$(cat "$PRIV_KEY")
NODE_A_PUB=$(cat "$PUB_KEY")

if [ -f "$CONF_FILE" ]; then
  echo "Backing up existing $CONF_FILE to $CONF_FILE.bak..."
  cp "$CONF_FILE" "$CONF_FILE.bak"
fi

cat > "$CONF_FILE" << EOF
[Interface]
# Node A Laptop Tunnel IP
Address = 10.100.0.1/24
PrivateKey = $NODE_A_PRIV

[Peer]
# Node B (Azure Linux VM)
# Replace PLACEHOLDER_AZURE_NODE_B_PUBLIC_KEY with the public key from Node B
PublicKey = PLACEHOLDER_AZURE_NODE_B_PUBLIC_KEY
# Replace PLACEHOLDER_AZURE_NODE_B_PUBLIC_IP with your assigned Azure Public IP
Endpoint = PLACEHOLDER_AZURE_NODE_B_PUBLIC_IP:51820
# Route traffic for Node B worker (10.100.0.2) and Node B guest microVMs (192.168.200.0/24)
AllowedIPs = 10.100.0.2/32, 192.168.200.0/24
PersistentKeepalive = 25
EOF

chmod 600 "$CONF_FILE"

echo
echo "======================================================================"
echo "Node A WireGuard Configuration Generated at $CONF_FILE"
echo "Node A Public Key: $NODE_A_PUB"
echo
echo "Next Steps:"
echo "1. On Node B (Azure VM), paste Node A's Public Key into:"
echo "   /etc/wireguard/wg0.conf as the Peer PublicKey."
echo "2. On Node A (this machine), edit $CONF_FILE:"
echo "   - Replace PLACEHOLDER_AZURE_NODE_B_PUBLIC_KEY with Node B's public key"
echo "   - Replace PLACEHOLDER_AZURE_NODE_B_PUBLIC_IP with Node B's Azure Public IP"
echo "3. Bring up the tunnel on Node A:"
echo "   sudo wg-quick up wg0"
echo "4. Verify connectivity using: bash deploy/azure/verify_azure_deployment.sh"
echo "======================================================================"
