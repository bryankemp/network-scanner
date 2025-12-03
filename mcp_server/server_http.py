#!/usr/bin/env python3
"""
Network Scanner MCP Server - HTTP Transport
Runs the FastMCP server with SSE transport for container deployment.
"""
import os
import sys

# Add backend to path for model imports
# Check if running in container (has /app) or local environment
if os.path.exists('/app'):
    sys.path.insert(0, '/app')
else:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import the FastMCP server instance from server
from server import mcp

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Network Scanner MCP Server (HTTP/SSE Transport)")
    print("📡 Listening on http://0.0.0.0:8001")
    print("🔧 Available endpoints:")
    print("   - SSE:    http://localhost:8001/sse")
    print("   - Tools:  http://localhost:8001/tools")
    print()
    
    # Get the SSE app from FastMCP
    app = mcp.sse_app()
    
    # Run with uvicorn on port 8001
    uvicorn.run(app, host='0.0.0.0', port=8001)
