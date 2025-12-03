#!/bin/bash
set -e

# Fix permissions on mounted volumes
echo "Fixing permissions on mounted volumes..."
chown -R root:root /app/scan_outputs /app/database /app/*.db 2>/dev/null || true

# Create scan_outputs if it doesn't exist
mkdir -p /app/scan_outputs

# Run as root for nmap OS detection capabilities
echo "Starting application as root (required for nmap OS detection)..."
exec "$@"
