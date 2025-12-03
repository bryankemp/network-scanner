# Network Scanner

A comprehensive network scanning and management solution with a modern web interface, RESTful API, and AI integration via Model Context Protocol (MCP).

**Author:** Bryan Kemp <bryan@kempville.com>  
**License:** MIT  
**Version:** 1.0.0

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Architecture](#architecture)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [MCP Integration](#mcp-integration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Core Scanning Capabilities
- 🔍 **Parallel Network Scanning** - Efficient multi-network CIDR scanning
- 🖥️ **Virtual Machine Detection** - Automatic identification of VMs and containers
- 🔐 **Service Discovery** - Comprehensive port scanning with service/version detection
- 🌐 **Network Topology** - Traceroute mapping and visualization
- 📊 **OS Fingerprinting** - Operating system detection with accuracy scoring

### Scheduled Scanning
- ⏰ **Cron-based Schedules** - Create recurring scans with flexible cron expressions
- 📅 **Pre-configured Presets** - Common schedules (hourly, daily, weekly, etc.)
- 🔄 **Manual Trigger** - On-demand execution of scheduled scans

### Reporting & Visualization
- 📄 **HTML Reports** - Detailed, styled network scan reports
- 📊 **Excel Exports** - Structured data in XLSX format
- 🗺️ **Network Diagrams** - Auto-generated topology maps (PNG/SVG)

### Web Interface
- 🎨 **Modern Flutter UI** - Responsive Material Design 3 interface
- 📱 **Mobile-Ready** - Works on desktop, tablet, and mobile
- 🌓 **Dark/Light Themes** - Automatic theme switching
- 🔒 **Role-based Access** - Admin and user roles
- 🔐 **JWT Authentication** - Secure token-based authentication

### AI Integration (MCP)
- 🤖 **Claude/Warp AI Integration** - Query scan data using natural language
- 💬 **Conversational Queries** - "Show me all VMs" or "What services are running on 192.168.1.10?"
- 📈 **Network Statistics** - Get insights via AI assistants

## 🚀 Quick Start

### Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/network-scan.git
cd network-scan

# Set up development environment
python3 setup.py dev

# Run tests
python3 setup.py test

# Start the backend server
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`  
API documentation at `http://localhost:8000/docs`

### Docker Setup

```bash
# Build and run
python3 setup.py docker

# Or use docker-compose
docker-compose up -d
```

### Service Installation

```bash
# Install as system service (macOS/Linux)
python3 setup.py service
```

## 📦 Installation

### Prerequisites

**Required:**
- Python 3.8+
- nmap

**Optional:**
- Flutter 3.9+ (for web UI)
- Docker (for containers)
- Graphviz (for diagrams)

### Manual Installation

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend (optional)
cd frontend
flutter pub get

# MCP Server
cd mcp_server
pip install -r requirements.txt
```

## 🏗️ Architecture

```
network-scan/
├── backend/          # FastAPI REST API
├── frontend/         # Flutter web app
├── mcp_server/       # AI integration
├── tests/            # Test suite
├── setup.py          # Setup automation
└── run_tests.py      # Test runner
```

**Tech Stack:** FastAPI, Flutter, SQLite, nmap, MCP

## 💻 Usage

### API Examples

```bash
# Create scan
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{"network_range": ["192.168.1.0/24"]}'

# Get scan details
curl http://localhost:8000/api/scans/1

# Download reports
curl http://localhost:8000/api/scans/1/artifacts/html -o report.html
curl http://localhost:8000/api/scans/1/artifacts/xlsx -o report.xlsx
```

### Web Interface

Navigate to `http://localhost:8000`

**Default Credentials:**
- Username: `admin`
- Password: `Admin123!`
- **⚠️ Change on first login!**

## 📚 API Documentation

Interactive docs: `http://localhost:8000/docs`

### Key Endpoints

- `POST /api/scans` - Create scan
- `GET /api/scans` - List scans
- `POST /api/schedules` - Create schedule
- `GET /api/hosts/unique` - Latest host data
- `GET /api/stats` - Network statistics
- `POST /api/auth/login` - Authentication

## 🤖 MCP Integration

### Available Tools

- `list_scans` - List all scans
- `query_hosts` - Search hosts
- `get_host_services` - Get services for host
- `get_network_stats` - Network statistics
- `list_vms` - List VMs/containers
- `search_service` - Find service on network

### Configuration

**Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Warp AI:** `~/.warp/mcp_config.json`

```json
{
  "mcpServers": {
    "network-scanner": {
      "command": "python3",
      "args": ["/path/to/network-scan/mcp_server/server.py"],
      "env": {
        "DATABASE_PATH": "/path/to/network-scan/network_scanner.db"
      }
    }
  }
}
```

## 🛠️ Development

```bash
# Run with auto-reload
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Code quality
black backend/ --line-length 100
ruff check backend/

# Tests
python3 setup.py test
```

## 🧪 Testing

**Total: 92 tests** (33 backend, 38 MCP, 21 frontend)

```bash
# All tests
python3 setup.py test

# Individual components
cd backend && pytest tests/ -v
cd mcp_server && pytest test_mcp_server.py -v
cd frontend && flutter test
```

## 🚀 Deployment

### Docker

```bash
python3 setup.py docker
docker-compose -f docker-compose.production.yml up -d
```

### System Service

```bash
python3 setup.py service

# Manage service
# macOS: launchctl list | grep network-scanner
# Linux: sudo systemctl status network-scanner
```

### Environment Variables

Create `backend/.env`:

```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
SCAN_PARALLELISM=8
```

## 🔧 Troubleshooting

**nmap not found**
```bash
# macOS
brew install nmap

# Linux
sudo apt-get install nmap
```

**Permission denied**
```bash
# Linux: Grant nmap capabilities
sudo setcap cap_net_raw,cap_net_admin+eip $(which nmap)
```

**Database locked**

For high concurrency, use PostgreSQL instead of SQLite.

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 📞 Support

- **Email:** bryan@kempville.com
- **Issues:** GitHub Issues

---

**Made with ❤️ by Bryan Kemp**
