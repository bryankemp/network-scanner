#!/bin/bash
set -e

# Fix permissions on mounted volumes
echo "Fixing permissions on mounted volumes..."

# Create necessary directories with proper permissions
mkdir -p /app/scan_outputs
mkdir -p /app/data/database

# Ensure directories are writable
chmod -R 755 /app/scan_outputs /app/data

# Run as root for nmap OS detection capabilities
echo "Starting application as root (required for nmap OS detection)..."
exec "$@"
