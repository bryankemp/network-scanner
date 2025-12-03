# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
Network Scanner is a FastAPI-based web service that performs comprehensive network scanning using nmap. It discovers hosts, detects services/OS/VMs, generates multiple report formats (HTML, Excel, PNG diagrams), and provides AI integration via MCP (Model Context Protocol).

## Project Structure
Multi-component architecture:
- **`backend/`** - FastAPI REST API and core scanning logic
- **`frontend/`** - Flutter web application (Material Design 3)
- **`mcp_server/`** - AI integration via Model Context Protocol
- **`tests/`** - Backend integration tests
- **`setup.py`** - Automated environment setup and service installation
- **`run_tests.py`** - Comprehensive test runner with reporting

## Development Commands

### Quick Setup (Automated)
```bash
# Set up complete development environment (auto-installs missing tools)
python3 setup.py dev

# Install missing tools only (nmap, Flutter, Docker via snap/apt)
python3 setup.py install-tools

# Run comprehensive test suite (all components + linting + health checks)
python3 run_tests.py

# Install as system service (macOS launchd or Linux systemd)
python3 setup.py service

# Build and run Docker containers
python3 setup.py docker

# Clean development artifacts
python3 setup.py clean
```

**Note:** On Ubuntu/Linux, `setup.py dev` will automatically install:
- **nmap** via apt (with capabilities for non-root scanning)
- **Flutter** via snap (if missing)
- **Docker** via snap (if missing)

### Backend Development
```bash
# Start development server (with auto-reload)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Start production server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# API documentation
open http://localhost:8000/docs  # or http://localhost:8000/docs
```

### Frontend Development
```bash
cd frontend

# Install dependencies
flutter pub get

# Run development server
flutter run -d chrome

# Build for web
flutter build web

# Run frontend tests
flutter test
```

### Testing
```bash
# Comprehensive test suite (92 tests: backend, MCP, frontend, linting, health)
python3 run_tests.py

# Backend unit tests only
cd backend
pytest tests/ -v

# Single test file
pytest tests/test_api.py -v

# MCP server tests
pytest mcp_server/test_mcp_server.py -v

# Frontend tests
cd frontend
flutter test
```

### Linting and Code Quality
```bash
# Format code with black
black backend/ --line-length 100

# Lint with ruff
ruff check backend/ --target-version py38
```

### Database Management
```bash
# Database is SQLite and auto-initializes on first run
# Location: ./network_scanner.db

# To reset database (delete all scans)
rm network_scanner.db

# Scan outputs stored in: ./scan_outputs/
```

## Architecture

### Backend Structure (`backend/app/`)
The FastAPI application follows a clean architecture pattern:

- **`main.py`**: API endpoints and FastAPI app configuration
  - Scans: POST/GET/DELETE operations
  - Schedules: CRUD operations for recurring scans
  - Artifacts: File serving (HTML, Excel, PNG, XML)
  - Stats: Network statistics and host queries
  - Health check endpoint
  
- **`models/`**: SQLAlchemy ORM models
  - `Scan`: Tracks scan metadata, status, progress
  - `ScanSchedule`: Recurring scan schedules with cron expressions
  - `Host`: Discovered devices with OS, hostname, VM detection
  - `Port`: Services/ports per host
  - `Artifact`: Generated files (HTML, Excel, diagrams)
  - `TracerouteHop`: Network topology data
  - `User`, `Settings`: Authentication and configuration
  
- **`schemas/`**: Pydantic models for request/response validation
  
- **`scanner/`**: Core scanning logic
  - `orchestrator.py`: Coordinates scan workflow (discovery → parallel host scans → parsing → reports)
  - `nmap_runner.py`: Executes nmap commands with proper flags
  - `parser.py`: Parses nmap XML output into structured data
  - `report_gen.py`: Generates HTML, Excel, and Graphviz diagrams
  - `network_detection.py`: Auto-detects current network CIDR
  - `stuck_scan_monitor.py`: Monitors and handles hung scans
  
- **`scheduler/`**: Scheduled scan management
  - `scheduler.py`: APScheduler-based background service for cron-based recurring scans
  - Automatically starts on app startup, gracefully shuts down
  - Manages schedule lifecycle (add/update/remove/trigger)
  
- **`auth/`**: Authentication system
  - `security.py`: JWT token generation and validation
  - `dependencies.py`: FastAPI dependency injection for auth
  
- **`api/`**: API route organization (if using router pattern)
- **`config.py`**: Application settings (scan parallelism, paths, database URL)
- **`database.py`**: SQLAlchemy session management

### Frontend Structure (`frontend/`)
Flutter web application with Material Design 3:
- State management and API client for backend communication
- Responsive design for desktop, tablet, mobile
- Dark/light theme support
- Real-time scan progress updates

### Test Structure (`tests/`)
Comprehensive integration tests:
- `test_api.py`: API endpoint tests
- `test_authentication.py`: Auth flow and JWT tests
- `test_models.py`: Database model tests
- `test_scan_orchestration.py`: End-to-end scan workflow tests
- `test_scheduler.py`: Scheduled scan tests
- `test_mcp_and_monitoring.py`: MCP server and monitoring tests
- `conftest.py`: Shared pytest fixtures

### Scanning Workflow
1. **Discovery Phase (0-15%)**: Fast ping scan across all networks to find live hosts
2. **Detailed Scanning (20-90%)**: Parallel comprehensive scans of discovered hosts
   - OS detection with accuracy scores
   - Service/version detection
   - Traceroute for topology mapping
   - NSE scripts (banner, SSL, HTTP info)
   - VM/container detection (MAC vendor, OS fingerprints)
3. **Report Generation (90-100%)**: Create HTML, Excel, PNG/SVG diagrams

### Key Technical Decisions
- **Parallel Scanning**: Uses `ThreadPoolExecutor` with 8 concurrent workers (configurable)
- **Two-Phase Scanning**: Discovery first to avoid wasting time on comprehensive scans of non-existent hosts
- **Multi-Network CIDR Support**: Single scan can cover multiple networks (e.g., `["192.168.1.0/24", "10.0.0.0/24"]`)
- **SQLite**: Simple deployment, no separate database server needed
- **Authentication Disabled**: Simplified for MVP/development; JWT infrastructure present but not enforced

### Scheduled Scans (`backend/app/scheduler/`)
Automatic recurring scans using cron expressions:
- Background scheduler service using APScheduler
- Full CRUD API for managing schedules
- Next run time calculation and last run tracking
- Manual trigger capability
- See `SCHEDULING.md` for full documentation

### MCP Server (`mcp_server/`)
Provides AI assistant integration for querying scan data:
- 7 tools: list_scans, get_scan_details, query_hosts, get_host_services, get_network_stats, list_vms, search_service
- Read-only access to SQLite database
- Configure in Claude Desktop or Warp AI settings (see `mcp_server/README.md`)

## Project-Specific Patterns

### Database Session Management
Always use `Depends(get_db)` for database sessions in endpoints:
```python
@app.post("/api/scans")
async def create_scan(scan_data: ScanCreate, db: Session = Depends(get_db)):
    # db session automatically handled
```

### Background Tasks
Long-running scans use FastAPI's `BackgroundTasks`:
```python
background_tasks.add_task(run_scan_background, scan.id, networks, db)
```

### Progress Tracking
Scans update `progress_percent` (0-100) and `progress_message` in database for real-time status:
```python
scan.progress_percent = 50
scan.progress_message = "Parsing scan results..."
self.db.commit()
```

### VM Detection
Enhanced detection uses multiple signals:
- MAC vendor matching (VMware, Xen, QEMU, Parallels)
- OS fingerprint patterns (Docker, LXC, VM-specific kernels)
- Network topology analysis for container patterns

## Configuration

### Key Settings (`backend/app/config.py`)
```python
scan_parallelism: int = 8  # Concurrent host scans
scan_output_dir: str = "./scan_outputs"  # Report storage
database_url: str = "sqlite:///./network_scanner.db"
```

### Environment Variables
Create `.env` file in `backend/` directory:
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
SCAN_PARALLELISM=8
```

## Common Development Tasks

### Adding a New API Endpoint
1. Define Pydantic schema in `backend/app/schemas/`
2. Add endpoint in `backend/app/main.py`
3. Use `Depends(get_db)` for database access
4. Follow existing patterns for error handling (HTTPException)

### Modifying Scan Behavior
Edit `backend/app/scanner/nmap_runner.py`:
- `discover_hosts()`: Fast ping scan to find live IPs
- `run_host_scan()`: Detailed per-host comprehensive scan
- Adjust nmap flags carefully (some require root/sudo)

### Adding Report Formats
Extend `backend/app/scanner/report_gen.py`:
1. Generate new format in function
2. Add to `ArtifactType` enum in `models/`
3. Update orchestrator to save artifact
4. Add media type mapping in artifact endpoint

### Extending VM Detection
Edit `backend/app/scanner/parser.py` → `detect_enhanced_vm()`:
- Add MAC vendor patterns
- Include OS fingerprint signatures
- Update VM type classification logic

## Important Notes

### nmap Requirements
- Ubuntu/Debian: `sudo apt-get install nmap`
- macOS: `brew install nmap`
- Some features require elevated privileges (OS detection with `-O`)
- Traceroute typically needs root/sudo
- Linux: Grant nmap capabilities for non-root scanning: `sudo setcap cap_net_raw,cap_net_admin+eip $(which nmap)`

### Performance Tuning
- Adjust `scan_parallelism` in config.py (default: 8)
- For large networks, consider smaller CIDR blocks
- Discovery phase is fast; detailed scans are time-intensive

### Authentication Status
Authentication infrastructure exists but is **disabled for development**:
- JWT tokens implemented but not enforced
- Only `/api/auth/me` requires authentication
- For production, re-enable auth checks in endpoints

### File Locations
- Database: `./network_scanner.db` (SQLite)
- Scan outputs: `./scan_outputs/scan_N.*` (HTML, XLSX, PNG, XML)
- Generated on each scan, linked via `Artifact` table

## External References
- [nmap official documentation](https://nmap.org/book/man.html)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## Quick Reference
For API usage examples and CIDR reference, see `QUICK_REFERENCE.md`
For detailed implementation status, see `IMPLEMENTATION_STATUS.md`
