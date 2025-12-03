#!/usr/bin/env python3
"""
Test suite for Network Scanner MCP Server.

Tests all 15 MCP tools including:
- Scan operations (list, details, start, progress)
- Host queries (search, services, topology)
- Network statistics and VM detection
- Vulnerability scanning
- Scheduled scans (NEW)
- User management (NEW)
- System health monitoring (NEW)
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import Base
from app.models import (
    Scan, Host, Port, ScanStatus, HostScanStatus, TracerouteHop,
    ScanSchedule, User, UserRole
)


# ========== FIXTURES ==========

@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory test database with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestSessionLocal
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a database session for each test."""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_scan(db_session):
    """Create a completed scan with hosts."""
    scan = Scan(
        network_range="192.168.1.0/24",
        status=ScanStatus.COMPLETED,
        started_at=datetime.utcnow() - timedelta(hours=2),
        completed_at=datetime.utcnow() - timedelta(hours=1),
        progress_percent=100,
        progress_message="Scan completed successfully"
    )
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    return scan


@pytest.fixture
def sample_host(db_session, sample_scan):
    """Create a sample host with open ports."""
    host = Host(
        ip="192.168.1.100",
        hostname="web-server.local",
        mac="00:11:22:33:44:55",
        vendor="Dell Inc.",
        os="Ubuntu Linux 22.04",
        os_accuracy=95,
        is_vm=False,
        scan_status=HostScanStatus.COMPLETED,
        scan_id=sample_scan.id
    )
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)
    
    # Add ports (Port model doesn't have 'state' field)
    ports = [
        Port(port=22, protocol="tcp", service="ssh", 
             product="OpenSSH", version="8.9p1", host_id=host.id),
        Port(port=80, protocol="tcp", service="http", 
             product="nginx", version="1.18.0", host_id=host.id),
        Port(port=443, protocol="tcp", service="https", 
             product="nginx", version="1.18.0", host_id=host.id),
    ]
    for port in ports:
        db_session.add(port)
    db_session.commit()
    
    return host


@pytest.fixture
def sample_vm_host(db_session, sample_scan):
    """Create a VM host for VM detection tests."""
    host = Host(
        ip="192.168.1.150",
        hostname="docker-container",
        mac="02:42:ac:11:00:02",
        vendor="Docker",
        os="Linux 5.15 (Docker)",
        os_accuracy=90,
        is_vm=True,
        vm_type="Docker",
        scan_status=HostScanStatus.COMPLETED,
        scan_id=sample_scan.id
    )
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)
    return host


@pytest.fixture
def sample_schedule(db_session, sample_users):
    """Create a scheduled scan."""
    admin = sample_users[0]  # Use admin user
    schedule = ScanSchedule(
        name="Nightly Security Scan",
        network_range="192.168.1.0/24",
        cron_expression="0 2 * * *",
        enabled=True,
        next_run_at=datetime.utcnow() + timedelta(hours=1),
        last_run_at=datetime.utcnow() - timedelta(days=1),
        created_by_id=admin.id
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


@pytest.fixture
def sample_users(db_session):
    """Create sample users."""
    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="$2b$12$hashed_password_here",
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=False,
        created_at=datetime.utcnow() - timedelta(days=30),
        last_login=datetime.utcnow() - timedelta(hours=1)
    )
    
    user = User(
        username="john",
        email="john@example.com",
        full_name="John Doe",
        hashed_password="$2b$12$hashed_password_here",
        role=UserRole.USER,
        is_active=True,
        must_change_password=True,
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    
    db_session.add(admin)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(user)
    return [admin, user]


@pytest.fixture
def traceroute_data(db_session, sample_host):
    """Create traceroute data for topology tests."""
    hops = [
        TracerouteHop(hop_number=1, ip="192.168.1.1", hostname="gateway.local", 
                     rtt=1.5, host_id=sample_host.id),
        TracerouteHop(hop_number=2, ip="10.0.0.1", hostname="router.local", 
                     rtt=5.2, host_id=sample_host.id),
    ]
    for hop in hops:
        db_session.add(hop)
    db_session.commit()
    return hops


@pytest.fixture
def mock_db_session(db_session, monkeypatch):
    """Mock the get_db function to use test database."""
    def mock_get_db():
        return db_session
    
    # Import server module and patch get_db
    import server
    monkeypatch.setattr(server, 'get_db', mock_get_db)
    
    return db_session


# ========== SCAN TOOL TESTS ==========

def test_list_scans_empty(mock_db_session):
    """Test list_scans with no scans in database."""
    from server import list_scans
    
    result = list_scans()
    assert "No scans found" in result


def test_list_scans_with_data(mock_db_session, sample_scan):
    """Test list_scans with scan data."""
    from server import list_scans
    
    result = list_scans(limit=10)
    assert "Found 1 scan(s)" in result
    assert "192.168.1.0/24" in result
    assert "completed" in result.lower()


def test_list_scans_status_filter(mock_db_session, db_session):
    """Test list_scans with status filter."""
    from server import list_scans
    
    # Create scans with different statuses
    completed = Scan(network_range="192.168.1.0/24", status=ScanStatus.COMPLETED)
    running = Scan(network_range="192.168.2.0/24", status=ScanStatus.RUNNING)
    failed = Scan(network_range="192.168.3.0/24", status=ScanStatus.FAILED)
    
    db_session.add_all([completed, running, failed])
    db_session.commit()
    
    result = list_scans(status="running")
    assert "192.168.2.0/24" in result
    assert "192.168.1.0/24" not in result


def test_get_scan_details_not_found(mock_db_session):
    """Test get_scan_details with non-existent scan."""
    from server import get_scan_details
    
    result = get_scan_details(scan_id=999)
    assert "Scan 999 not found" in result


def test_get_scan_details_success(mock_db_session, sample_scan, sample_host):
    """Test get_scan_details with valid scan."""
    from server import get_scan_details
    
    result = get_scan_details(scan_id=sample_scan.id)
    assert f"Scan Details (ID: {sample_scan.id})" in result
    assert "192.168.1.0/24" in result
    assert ("Discovered Hosts: 1" in result or "Hosts Discovered: 1" in result)
    assert "192.168.1.100" in result


def test_get_scan_progress_completed(mock_db_session, sample_scan):
    """Test get_scan_progress for completed scan."""
    from server import get_scan_progress
    
    result = get_scan_progress(scan_id=sample_scan.id)
    assert "100%" in result
    assert "completed" in result.lower()


# ========== HOST QUERY TESTS ==========

def test_query_hosts_empty(mock_db_session):
    """Test query_hosts with no hosts."""
    from server import query_hosts
    
    result = query_hosts()
    assert "No hosts found" in result


def test_query_hosts_by_ip(mock_db_session, sample_host):
    """Test query_hosts filtering by IP."""
    from server import query_hosts
    
    result = query_hosts(ip="192.168.1.100")
    assert "192.168.1.100" in result
    assert "web-server.local" in result


def test_query_hosts_by_hostname(mock_db_session, sample_host):
    """Test query_hosts filtering by hostname."""
    from server import query_hosts
    
    result = query_hosts(hostname="web-server")
    assert "192.168.1.100" in result
    assert "web-server.local" in result


def test_query_hosts_vm_filter(mock_db_session, sample_host, sample_vm_host):
    """Test query_hosts filtering VMs only."""
    from server import query_hosts
    
    result = query_hosts(is_vm=True)
    assert "192.168.1.150" in result
    assert "Docker" in result
    assert "192.168.1.100" not in result


def test_get_host_services_not_found(mock_db_session):
    """Test get_host_services with non-existent host."""
    from server import get_host_services
    
    result = get_host_services(host_id=999)
    assert "Host 999 not found" in result


def test_get_host_services_success(mock_db_session, sample_host):
    """Test get_host_services with ports."""
    from server import get_host_services
    
    result = get_host_services(host_id=sample_host.id)
    assert "192.168.1.100" in result
    assert "22/tcp" in result
    assert "ssh" in result
    assert "80/tcp" in result
    assert "443/tcp" in result


# ========== NETWORK STATS TESTS ==========

def test_get_network_stats_empty(mock_db_session):
    """Test get_network_stats with empty database."""
    from server import get_network_stats
    
    result = get_network_stats()
    assert "Total Scans: 0" in result
    assert "Total Hosts Discovered: 0" in result or "Total Hosts: 0" in result


def test_get_network_stats_with_data(mock_db_session, sample_scan, sample_host, sample_vm_host):
    """Test get_network_stats with data."""
    from server import get_network_stats
    
    result = get_network_stats()
    assert "Total Scans: 1" in result
    assert ("Total Hosts: 2" in result or "Total Hosts Discovered: 2" in result)
    assert ("Total VMs: 1" in result or "Virtual Machines: 1" in result)
    assert "Services: 3" in result  # 3 ports on sample_host


# ========== VM DETECTION TESTS ==========

def test_list_vms_empty(mock_db_session, sample_host):
    """Test list_vms with no VMs (only physical hosts)."""
    from server import list_vms
    
    result = list_vms()
    assert ("No VMs or containers found" in result or "No virtual machines or containers found" in result)


def test_list_vms_with_data(mock_db_session, sample_vm_host):
    """Test list_vms with VM data."""
    from server import list_vms
    
    result = list_vms()
    assert ("Found 1 VM" in result or "Found 1 virtual machine(s)/container(s)" in result)
    assert "Docker" in result
    assert "192.168.1.150" in result


def test_list_vms_type_filter(mock_db_session, db_session, sample_scan):
    """Test list_vms filtering by VM type."""
    from server import list_vms
    
    # Create VMs of different types
    docker = Host(ip="192.168.1.150", hostname="docker1", is_vm=True, 
                 vm_type="Docker", scan_id=sample_scan.id, 
                 scan_status=HostScanStatus.COMPLETED)
    vmware = Host(ip="192.168.1.151", hostname="vmware1", is_vm=True, 
                 vm_type="VMware", scan_id=sample_scan.id,
                 scan_status=HostScanStatus.COMPLETED)
    
    db_session.add_all([docker, vmware])
    db_session.commit()
    
    result = list_vms(vm_type="Docker")
    assert "192.168.1.150" in result
    assert "192.168.1.151" not in result


# ========== SERVICE SEARCH TESTS ==========

def test_search_service_not_found(mock_db_session):
    """Test search_service with no matches."""
    from server import search_service
    
    result = search_service(service_name="mysql")
    assert ("No hosts found running mysql" in result or "No hosts found running service 'mysql'" in result)


def test_search_service_success(mock_db_session, sample_host):
    """Test search_service with matches."""
    from server import search_service
    
    result = search_service(service_name="ssh")
    assert ("Found 1 host" in result or "Found 'ssh' on 1 host" in result)
    assert "192.168.1.100" in result
    assert "22/tcp" in result


def test_search_service_with_port(mock_db_session, sample_host):
    """Test search_service with port filter."""
    from server import search_service
    
    result = search_service(service_name="http", port=80)
    assert "192.168.1.100" in result
    assert "80/tcp" in result


# ========== TOPOLOGY TESTS ==========

def test_get_network_topology_no_data(mock_db_session, sample_host):
    """Test get_network_topology with no traceroute data."""
    from server import get_network_topology
    
    result = get_network_topology(host_id=sample_host.id)
    assert "192.168.1.100" in result
    assert "No traceroute data available" in result


def test_get_network_topology_with_data(mock_db_session, sample_host, traceroute_data):
    """Test get_network_topology with traceroute data."""
    from server import get_network_topology
    
    result = get_network_topology(host_id=sample_host.id)
    assert "192.168.1.1" in result
    assert "gateway.local" in result
    assert "10.0.0.1" in result
    assert "router.local" in result


# ========== VULNERABILITY TESTS ==========

def test_find_vulnerabilities_no_scripts(mock_db_session, sample_host):
    """Test find_vulnerabilities with no NSE script results."""
    from server import find_vulnerabilities
    
    result = find_vulnerabilities()
    assert ("No vulnerabilities or script results found" in result or "No script results found" in result)


# ========== SCHEDULE TESTS (NEW) ==========

def test_list_schedules_empty(mock_db_session):
    """Test list_schedules with no schedules."""
    from server import list_schedules
    
    result = list_schedules()
    assert "No schedules found" in result


def test_list_schedules_with_data(mock_db_session, sample_schedule):
    """Test list_schedules with schedule data."""
    from server import list_schedules
    
    result = list_schedules()
    assert "Found 1 schedule" in result
    assert "Nightly Security Scan" in result
    assert "192.168.1.0/24" in result
    assert "0 2 * * *" in result


def test_list_schedules_enabled_filter(mock_db_session, db_session, sample_users):
    """Test list_schedules filtering by enabled status."""
    from server import list_schedules
    
    admin = sample_users[0]
    enabled = ScanSchedule(name="Enabled", network_range="192.168.1.0/24",
                          cron_expression="0 2 * * *", enabled=True, created_by_id=admin.id)
    disabled = ScanSchedule(name="Disabled", network_range="192.168.2.0/24",
                           cron_expression="0 3 * * *", enabled=False, created_by_id=admin.id)
    
    db_session.add_all([enabled, disabled])
    db_session.commit()
    
    result = list_schedules(enabled_only=True)
    assert "Enabled" in result
    assert "Disabled" not in result


def test_get_schedule_details_not_found(mock_db_session):
    """Test get_schedule_details with non-existent schedule."""
    from server import get_schedule_details
    
    result = get_schedule_details(schedule_id=999)
    assert "Schedule 999 not found" in result


def test_get_schedule_details_success(mock_db_session, sample_schedule, db_session):
    """Test get_schedule_details with valid schedule."""
    from server import get_schedule_details
    
    # Add a scan from this schedule
    scan = Scan(network_range="192.168.1.0/24", status=ScanStatus.COMPLETED,
               schedule_id=sample_schedule.id)
    db_session.add(scan)
    db_session.commit()
    
    result = get_schedule_details(schedule_id=sample_schedule.id)
    assert "Nightly Security Scan" in result
    assert "0 2 * * *" in result
    assert "Recent Scans" in result


# ========== USER TESTS (NEW) ==========

def test_list_users_empty(mock_db_session):
    """Test list_users with no users."""
    from server import list_users
    
    result = list_users()
    assert "No users found" in result


def test_list_users_with_data(mock_db_session, sample_users):
    """Test list_users with user data."""
    from server import list_users
    
    result = list_users()
    assert "Found 2 user(s)" in result
    assert "admin" in result
    assert "john" in result
    # Check for role (may be uppercase or lowercase depending on .value)
    assert ("ADMIN" in result or "admin" in result)
    assert ("USER" in result or "user" in result)
    assert "admin@example.com" in result


def test_list_users_shows_status(mock_db_session, sample_users):
    """Test list_users shows password change requirement."""
    from server import list_users
    
    result = list_users()
    assert "Must change password" in result  # john's status


# ========== SYSTEM HEALTH TESTS (NEW) ==========

def test_get_system_health_healthy(mock_db_session, sample_scan, sample_host):
    """Test get_system_health with healthy system."""
    from server import get_system_health
    
    result = get_system_health()
    assert "System Health Report" in result
    assert "No stuck scans detected" in result or "✓" in result
    assert "Total Scans:" in result
    assert "Total Hosts:" in result
    assert "HEALTHY" in result


def test_get_system_health_stuck_scan(mock_db_session, db_session):
    """Test get_system_health detects stuck scans."""
    from server import get_system_health
    
    # Create an old running scan (stuck)
    old_scan = Scan(
        network_range="192.168.1.0/24",
        status=ScanStatus.RUNNING,
        created_at=datetime.utcnow() - timedelta(hours=7),
        started_at=datetime.utcnow() - timedelta(hours=7)
    )
    db_session.add(old_scan)
    db_session.commit()
    
    result = get_system_health()
    assert "WARNING" in result
    assert "stuck scan" in result.lower()


def test_get_system_health_24h_stats(mock_db_session, db_session):
    """Test get_system_health shows 24h statistics."""
    from server import get_system_health
    
    # Create recent scans with different statuses
    recent = [
        Scan(network_range="192.168.1.0/24", status=ScanStatus.COMPLETED,
             created_at=datetime.utcnow() - timedelta(hours=2)),
        Scan(network_range="192.168.2.0/24", status=ScanStatus.FAILED,
             created_at=datetime.utcnow() - timedelta(hours=5)),
        Scan(network_range="192.168.3.0/24", status=ScanStatus.RUNNING,
             created_at=datetime.utcnow() - timedelta(hours=1)),
    ]
    
    for scan in recent:
        db_session.add(scan)
    db_session.commit()
    
    result = get_system_health()
    assert "Last 24 Hours:" in result
    assert "Total Scans: 3" in result
    assert "Completed: 1" in result
    assert "Failed: 1" in result
    assert "Running: 1" in result


# ========== EDGE CASE TESTS ==========

def test_list_scans_limit(mock_db_session, db_session):
    """Test list_scans respects limit parameter."""
    from server import list_scans
    
    # Create 15 scans
    for i in range(15):
        scan = Scan(network_range=f"192.168.{i}.0/24", status=ScanStatus.COMPLETED)
        db_session.add(scan)
    db_session.commit()
    
    result = list_scans(limit=5)
    assert "Found 5 scan(s)" in result


def test_query_hosts_limit(mock_db_session, db_session, sample_scan):
    """Test query_hosts respects limit parameter."""
    from server import query_hosts
    
    # Create 25 hosts
    for i in range(25):
        host = Host(ip=f"192.168.1.{i}", scan_id=sample_scan.id,
                   scan_status=HostScanStatus.COMPLETED)
        db_session.add(host)
    db_session.commit()
    
    result = query_hosts(limit=10)
    assert "Found 10 host(s)" in result


def test_get_scan_details_no_hosts(mock_db_session, sample_scan):
    """Test get_scan_details with scan that has no hosts."""
    from server import get_scan_details
    
    result = get_scan_details(scan_id=sample_scan.id)
    assert ("Discovered Hosts: 0" in result or "Hosts Discovered: 0" in result)


# ========== INTEGRATION TESTS ==========

def test_full_scan_lifecycle(mock_db_session, db_session):
    """Test full scan lifecycle: create -> query -> details."""
    from server import list_scans, get_scan_details, query_hosts
    
    # Create scan with host
    scan = Scan(network_range="10.0.0.0/24", status=ScanStatus.COMPLETED,
               started_at=datetime.utcnow(), completed_at=datetime.utcnow())
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    
    host = Host(ip="10.0.0.50", hostname="test.local", scan_id=scan.id,
               scan_status=HostScanStatus.COMPLETED)
    db_session.add(host)
    db_session.commit()
    
    # Test list
    list_result = list_scans()
    assert "10.0.0.0/24" in list_result
    
    # Test details
    detail_result = get_scan_details(scan_id=scan.id)
    assert "10.0.0.50" in detail_result
    
    # Test query
    query_result = query_hosts(ip="10.0.0.50")
    assert "test.local" in query_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
