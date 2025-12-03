# Network Scanner MCP Server

Modern MCP (Model Context Protocol) server implementation following the official specification, allowing AI assistants like Claude, Warp AI, and others to query your network scan data.

## 🎯 Features

- **Modern Implementation**: Built with FastMCP following official MCP specification
- **11 Powerful Tools**: Start scans, query scans, hosts, services, VMs, vulnerabilities, and topology
- **Clean Architecture**: Type-safe, well-documented, easy to extend
- **Multiple Transports**: Supports stdio (default), SSE, and Streamable HTTP
- **Production Ready**: Proper error handling and database management

## 🚀 Quick Setup

### 1. Install Dependencies

The server requires the MCP Python SDK (version 1.2.0+):

```bash
cd mcp_server
pip install "mcp[cli]>=1.2.0" sqlalchemy
```

### 2. Configure in Your AI Assistant

#### For Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "network-scanner": {
      "command": "python3",
      "args": [
        "/Users/bryan/Projects/network-scan/mcp_server/server.py"
      ]
    }
  }
}
```

#### For Warp AI

Add to Warp's MCP settings (same format as Claude Desktop):

```json
{
  "mcpServers": {
    "network-scanner": {
      "command": "python3",
      "args": [
        "/Users/bryan/Projects/network-scan/mcp_server/server.py"
      ]
    }
  }
}
```

### 3. Restart Your AI Assistant

After adding the configuration, restart Claude Desktop or Warp to load the MCP server.

## 🛠️ Available Tools

The MCP server provides 11 tools for managing and querying network scan data:

### 1. `start_scan` ⭐ NEW
Start a new network scan.

**Parameters:**
- `networks` (optional): List of networks in CIDR format (e.g., ["192.168.1.0/24", "10.0.0.0/24"])
  - If omitted, auto-detects current network

**Example:**
> "Start a scan of 192.168.1.0/24"
> "Scan my current network"
> "Start a scan of 10.0.0.0/24 and 172.16.0.0/16"

### 2. `list_scans`
List all network scans with optional filtering.

**Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed)
- `limit` (optional): Maximum scans to return (default: 10)

**Example:**
> "Show me the last 5 completed scans"

### 3. `get_scan_details`
Get detailed information about a specific scan including all discovered hosts.

**Parameters:**
- `scan_id` (required): The ID of the scan

**Example:**
> "Show me details of scan 3"

### 4. `query_hosts`
Search for hosts by IP, hostname, or properties.

**Parameters:**
- `ip` (optional): IP address filter (partial match)
- `hostname` (optional): Hostname filter (partial match)
- `is_vm` (optional): Filter for VMs only (true/false)
- `limit` (optional): Maximum hosts to return (default: 20)

**Example:**
> "Find all hosts with IP starting with 192.168.1"
> "Show me all virtual machines"

### 5. `get_host_services`
Get all open ports and services for a specific host.

**Parameters:**
- `host_id` (required): The ID of the host

**Example:**
> "What services are running on host 5?"

### 6. `get_network_stats`
Get overall network statistics.

**Parameters:** None

**Example:**
> "Give me network statistics"
> "How many VMs have been discovered?"

### 7. `list_vms`
List all detected virtual machines and containers.

**Parameters:**
- `vm_type` (optional): Filter by VM type (VMware, Docker, LXC, etc.)
- `limit` (optional): Maximum VMs to return (default: 50)

**Example:**
> "List all Docker containers"
> "Show me all virtual machines"

### 8. `search_service`
Find all hosts running a specific service.

**Parameters:**
- `service_name` (required): Service to search for
- `port` (optional): Specific port number

**Example:**
> "Which hosts are running SSH?"
> "Find all web servers"
> "Show me hosts with MySQL"

### 9. `get_network_topology`
Get network topology and traceroute information for a host.

**Parameters:**
- `host_id` (required): The ID of the host

**Example:**
> "Show me the network path to host 5"
> "What's the topology for this host?"

### 10. `find_vulnerabilities`
Search for hosts with specific NSE script results or vulnerabilities.

**Parameters:**
- `script_name` (optional): NSE script name to filter by

**Example:**
> "Find all SSL certificate information"
> "Show me HTTP title results"
> "Search for banner script output"

### 11. `get_scan_progress`
Get detailed progress for an in-progress scan including per-host status.

**Parameters:**
- `scan_id` (required): The ID of the scan

**Example:**
> "What's the progress of scan 2?"
> "Show me which hosts are currently being scanned"

## 💬 Usage Examples

Once configured, you can ask your AI assistant natural language questions:

- "Start a scan of my network" ⭐ NEW
- "Scan 192.168.1.0/24" ⭐ NEW
- "What scans have been completed?"
- "Show me all the hosts discovered in scan 1"
- "Find hosts running HTTP services"
- "List all Docker containers on the network"
- "Which hosts are virtual machines?"
- "What are the most common services on my network?"
- "Show me hosts in the 192.168.1.x range"

## 🔍 How It Works

The MCP server:
1. Connects to the same SQLite database as the main API
2. Can initiate new network scans (runs in background)
3. Provides read access to scan data
4. Formats results in a human-readable format
5. Runs separately from the FastAPI backend

## 🧪 Testing

You can test the MCP server using multiple methods:

### Method 1: MCP Inspector (Recommended)

The official MCP Inspector provides a web UI for testing:

```bash
cd mcp_server
mcp dev server.py
```

This will open a web interface where you can test all tools interactively.

### Method 2: Direct Execution

For advanced users who want to test via stdin:

```bash
cd mcp_server
python3 server.py
```

### Method 3: Test with AI Assistant

Configure it in Claude Desktop or Warp AI and ask questions naturally.

## 📊 Data Access

The MCP server can:
- ✅ Start new network scans
- ✅ Read all scan records and their status
- ✅ Access discovered hosts with full details
- ✅ Query open ports and services
- ✅ View VM/container detection results
- ✅ Get network statistics

It **cannot**:
- ❌ Delete data
- ❌ Access user credentials
- ❌ Modify system settings
- ❌ Cancel running scans

## 🏗️ Architecture

### Modern FastMCP Implementation

The server (`server.py`) uses the official FastMCP framework:

- **Declarative Tools**: Simple `@mcp.tool()` decorator pattern
- **Type Safety**: Python type hints automatically generate schemas
- **Auto Documentation**: Docstrings become tool descriptions
- **Multiple Transports**: Switch between stdio/SSE/HTTP with one line

### Key Improvements from Previous Version

| Feature | Previous | Current |
|---------|----------|----------|
| Framework | Raw MCP SDK | FastMCP |
| Code Lines | ~760 | ~680 |
| Tool Definition | Manual types.Tool() | @mcp.tool() decorator |
| Schema Generation | Manual | Automatic from type hints |
| Spec Compliance | 2024-11-05 | Latest (2025-03-26) |
| Decorator Pattern | No | ✅ Yes |
| Type Safety | Partial | ✅ Full |

## 🔒 Security Note

The MCP server accesses your network scan database directly. Only configure it in AI assistants you trust, as it can read all scan data.

## 🐛 Troubleshooting

### "Module 'mcp' not found"
```bash
pip install "mcp[cli]>=1.2.0"
```

### "Cannot connect to database"
Make sure the backend has been run at least once to create the database:
```bash
cd ../backend
python -m uvicorn app.main:app
```

### "Import error for app.models"
The MCP server needs the backend directory in its path. This is handled automatically by the `sys.path.insert` in `server.py`.

## 🚀 Advanced Usage

### Running with Different Transports

The server supports multiple transport modes:

```python
# stdio (default - for Claude Desktop, Warp AI)
mcp.run(transport='stdio')

# SSE (for web clients)
mcp.run(transport='sse', host='127.0.0.1', port=8001)

# Streamable HTTP (modern web transport)
mcp.run(transport='streamable-http', host='127.0.0.1', port=8001)
```

### Environment Variables

Customize the database location:

```bash
DATABASE_URL=sqlite:////path/to/custom.db python3 server.py
```

## 📖 Learn More

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Main Project README](../MVP_README.md)
