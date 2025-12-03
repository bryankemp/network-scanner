#!/bin/bash
# Setup script to add Network Scanner MCP server to Warp
# Configures connection to remote MCP server on slag.kempville.com

# Warp MCP config location
WARP_CONFIG_DIR="$HOME/Library/Application Support/warp-terminal"
WARP_CONFIG_FILE="$WARP_CONFIG_DIR/mcp_config.json"

# Remote server details
REMOTE_SERVER="slag.kempville.com"
REMOTE_PORT="8001"
REMOTE_URL="http://${REMOTE_SERVER}:${REMOTE_PORT}/sse"

# Create config directory if it doesn't exist
mkdir -p "$WARP_CONFIG_DIR"

# Create or update config file
if [ -f "$WARP_CONFIG_FILE" ]; then
    echo "Warp MCP config already exists at $WARP_CONFIG_FILE"
    echo "You'll need to manually add the network-scanner server."
    echo ""
    echo "Add this to your mcpServers section:"
    echo ""
    cat <<EOF
    "network-scanner": {
      "url": "$REMOTE_URL"
    }
EOF
else
    echo "Creating new Warp MCP config at $WARP_CONFIG_FILE"
    cat > "$WARP_CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "network-scanner": {
      "url": "$REMOTE_URL"
    }
  }
}
EOF
    echo "✅ Configuration created successfully!"
fi

echo ""
echo "📡 Configuration Details:"
echo "   Remote Server: $REMOTE_SERVER"
echo "   MCP Endpoint: $REMOTE_URL"
echo ""
echo "Next steps:"
echo ""
echo "1. Ensure the container is deployed and running on slag.kempville.com:"
echo "   ssh bryan@slag.kempville.com 'cd /path/to/network-scan && docker-compose up -d'"
echo ""
echo "2. Verify the MCP server is accessible:"
echo "   curl http://slag.kempville.com:8001/"
echo ""
echo "3. Restart Warp terminal to load the new configuration"
echo ""
echo "4. Try asking Warp AI:"
echo "   'Show me recent network scans'"
echo "   'List all discovered hosts'"
echo "   'Which hosts are running SSH?'"
echo ""
echo "💡 Note: The MCP server uses SSE (Server-Sent Events) transport"
echo "   Make sure port 8001 is accessible from your machine."
