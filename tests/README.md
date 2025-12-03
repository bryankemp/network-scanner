# Network Scanner Unit Tests

Comprehensive unit test suite for the Network Scanner application.

**Author:** Bryan Kemp <bryan@kempville.com>

## Test Coverage

This test suite provides coverage for the following critical components:

### 1. Authentication (`test_authentication.py`)
- **Password Security**: Bcrypt hashing and verification
- **JWT Tokens**: Access and refresh token generation/validation
- **Login Endpoint**: Valid/invalid credentials, missing fields, timestamp updates
- **Token Refresh**: Token refresh flow and validation
- **Current User Endpoint**: Protected endpoint access
- **Integration**: Full authentication workflow

### 2. Scan Orchestration (`test_scan_orchestration.py`)
- **Scan Initialization**: Status transitions from PENDING → RUNNING → COMPLETED
- **Discovery Phase**: Host discovery and progress updates (0-15%)
- **Host Scanning**: Parallel per-host comprehensive scans (20-90%)
- **Progress Tracking**: Real-time progress updates through all phases
- **Database Persistence**: Hosts, ports, and scan metadata
- **Report Generation**: HTML, XLSX, and network diagrams (90-100%)
- **Error Handling**: Graceful error handling and status updates
- **Multi-Network Support**: Scanning multiple network ranges

### 3. Scheduler Service (`test_scheduler.py`)
- **Lifecycle Management**: Start/stop scheduler, idempotent operations
- **Schedule Management**: Add, update, remove, and trigger schedules
- **Cron Expressions**: Standard (5-field) and extended (6-field) formats
- **Background Execution**: Threaded scan execution
- **Automatic Triggering**: Scheduled scans based on cron expressions
- **Database Updates**: last_run_at and next_run_at timestamps
- **Error Handling**: Graceful handling of scan failures

### 4. MCP Server & Monitoring (`test_mcp_and_monitoring.py`)
- **MCP start_scan Tool**: 
  - Scan creation and validation
  - CIDR format validation
  - Network auto-detection
  - Background thread execution
  - Status reporting
- **Stuck Scan Monitor**:
  - Diagnostic analysis (host status, runtime, processes)
  - Automatic detection (runtime exceeded, stalled progress, pending timeout)
  - Process termination (graceful → force kill)
  - Error messaging with diagnostics
  - Multiple scan handling

## Running Tests

### Prerequisites

Ensure all dependencies are installed:

```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test Files

```bash
# Authentication tests only
pytest tests/test_authentication.py -v

# Scan orchestration tests only
pytest tests/test_scan_orchestration.py -v

# Scheduler tests only
pytest tests/test_scheduler.py -v

# MCP and monitoring tests only
pytest tests/test_mcp_and_monitoring.py -v
```

### Run Specific Test Classes

```bash
# Test only login endpoint
pytest tests/test_authentication.py::TestLoginEndpoint -v

# Test only scan status transitions
pytest tests/test_scan_orchestration.py::TestScanOrchestration::test_scan_status_transitions -v

# Test only stuck scan detection
pytest tests/test_mcp_and_monitoring.py::TestStuckScanMonitor -v
```

### Run with Output

```bash
# Show print statements and logging
pytest tests/ -v -s

# Show detailed failure information
pytest tests/ -v --tb=long
```

## Test Fixtures

The test suite uses pytest fixtures defined in `conftest.py`:

- **`db_engine`**: In-memory SQLite database engine
- **`db_session`**: Database session for test isolation
- **`api_client`**: FastAPI TestClient with test database
- **`sample_scan`**: Pre-configured scan record
- **`sample_host`**: Pre-configured host record
- **`sample_port`**: Pre-configured port record
- **`sample_nmap_xml`**: Mock nmap XML output
- **`mock_nmap_runner`**: Mocked NMapRunner for unit tests

## Test Organization

### Unit Tests
Tests individual components in isolation using mocks and fixtures:
- Password hashing functions
- Token generation/validation
- Scan orchestrator methods
- Scheduler service methods
- Stuck scan monitor static methods

### Integration Tests
Tests interactions between multiple components:
- Full authentication flow
- Complete scan workflow
- Schedule lifecycle (create → trigger → update → remove)
- Multi-scan stuck detection

## Coverage Requirements

Target coverage for critical components:
- **Authentication**: >95% (security-critical)
- **Scan Orchestration**: >90% (core functionality)
- **Scheduler**: >85% (background service)
- **Monitoring**: >90% (reliability-critical)

View current coverage:
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    cd backend
    pytest tests/ --cov=app --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## Mocking Strategy

External dependencies are mocked to ensure:
- **Fast execution**: No actual network scans
- **Deterministic results**: Consistent test outcomes
- **Isolation**: Tests don't depend on external state

Mocked components:
- `NMapRunner` (discovery_hosts, run_host_scan)
- Network detection
- Report generation (HTML, XLSX, diagrams)
- Threading (for synchronous test execution)
- Process management (psutil)

## Troubleshooting

### Import Errors
If you encounter import errors, ensure you're running from the project root:
```bash
cd /Users/bryan/Projects/network-scan
PYTHONPATH=. pytest tests/
```

### Database Errors
Tests use in-memory SQLite. If you see database errors:
```bash
# Clear any cached database files
rm -f backend/*.db
rm -f tests/*.db
```

### Fixture Not Found
Ensure `conftest.py` is in the `tests/` directory and pytest can discover it:
```bash
pytest --fixtures tests/
```

## Future Enhancements

Planned test additions:
- [ ] WebSocket real-time scan progress tests
- [ ] Data retention/cleanup job tests
- [ ] User management endpoint tests
- [ ] Rate limiting tests
- [ ] Concurrent scan execution tests
- [ ] Performance/load tests for large networks

## Contributing

When adding new tests:

1. Follow existing naming conventions:
   - Test files: `test_<component>.py`
   - Test classes: `Test<ComponentName>`
   - Test methods: `test_<behavior>_<condition>`

2. Include docstrings explaining what is being tested

3. Use appropriate fixtures to minimize setup code

4. Mock external dependencies (network, filesystem, etc.)

5. Ensure tests are independent and can run in any order

6. Add integration tests for complex workflows

## License

Copyright © 2024 Bryan Kemp. All rights reserved.
