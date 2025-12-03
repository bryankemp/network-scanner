#!/bin/bash
# Start both the main FastAPI app and the MCP HTTP server

set -e

echo "🚀 Starting Network Scanner services..."

# Start FastAPI in the background
echo "📊 Starting FastAPI server on port 8000..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Give FastAPI time to start
sleep 2

# Start MCP HTTP server in the background
echo "🔌 Starting MCP HTTP server on port 8001..."
cd /app/mcp_server && python server_http.py &
MCP_PID=$!

echo "✅ Services started:"
echo "   - FastAPI: http://localhost:8000 (PID: $FASTAPI_PID)"
echo "   - MCP Server: http://localhost:8001 (PID: $MCP_PID)"
echo ""
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔧 MCP Tools: http://localhost:8001/tools"

# Wait for both processes
wait $FASTAPI_PID $MCP_PID
