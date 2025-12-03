"""
Pytest configuration and fixtures for network-scan tests.

This module provides reusable test fixtures including database sessions,
mock objects, and sample data for testing the network scanner application.
"""
import pytest
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import Base
# Import all models to ensure tables are created
from app.models import (
    Scan, Host, Port, Artifact, ScanStatus, HostScanStatus, ArtifactType,
    User, UserRole, ScanSchedule, TracerouteHop, Settings
)


@pytest.fixture(scope="function")
def db_engine():
    """
    Create an in-memory SQLite database engine for testing.
    
    Yields:
        Engine: SQLAlchemy engine connected to in-memory database
    """
    from unittest.mock import patch
    
    # Use file-based SQLite with shared cache for better thread safety
    engine = create_engine(
        "sqlite:///file:test_db?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    
    # Create a session factory that uses the test engine
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Patch SessionLocal globally so that scheduler and orchestrator use test database
    with patch('app.database.SessionLocal', TestSessionLocal), \
         patch('app.scheduler.scheduler.SessionLocal', TestSessionLocal), \
         patch('app.scanner.orchestrator.SessionLocal', TestSessionLocal):
        yield engine
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a database session for testing.
    
    Args:
        db_engine: Database engine fixture
        
    Yields:
        Session: SQLAlchemy session for database operations
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_scan(db_session):
    """
    Create a sample scan record for testing.
    
    Args:
        db_session: Database session fixture
        
    Returns:
        Scan: Sample scan with RUNNING status
    """
    scan = Scan(
        network_range="192.168.1.0/24",
        status=ScanStatus.RUNNING,
        started_at=datetime.utcnow(),
        progress_percent=50,
        progress_message="Scanning hosts..."
    )
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    return scan


@pytest.fixture
def sample_host(db_session, sample_scan):
    """
    Create a sample host record for testing.
    
    Args:
        db_session: Database session fixture
        sample_scan: Sample scan fixture
        
    Returns:
        Host: Sample host with completed scan status
    """
    host = Host(
        ip="192.168.1.100",
        hostname="test-server.local",
        mac="00:11:22:33:44:55",
        vendor="Test Vendor",
        os="Linux 5.15",
        os_accuracy=95,
        is_vm=False,
        scan_status=HostScanStatus.COMPLETED,
        scan_id=sample_scan.id
    )
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)
    return host


@pytest.fixture
def sample_port(db_session, sample_host):
    """
    Create a sample port record for testing.
    
    Args:
        db_session: Database session fixture
        sample_host: Sample host fixture
        
    Returns:
        Port: Sample open port (SSH on 22)
    """
    port = Port(
        port=22,
        protocol="tcp",
        service="ssh",
        product="OpenSSH",
        version="8.9p1",
        host_id=sample_host.id
    )
    db_session.add(port)
    db_session.commit()
    db_session.refresh(port)
    return port


@pytest.fixture
def sample_nmap_xml():
    """
    Provide sample nmap XML output for parser testing.
    
    Returns:
        str: XML string representing nmap scan output
    """
    return """<?xml version="1.0"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" start="1701234567" version="7.94">
  <host>
    <status state="up" reason="echo-reply"/>
    <address addr="192.168.1.100" addrtype="ipv4"/>
    <address addr="00:11:22:33:44:55" addrtype="mac" vendor="Test Vendor"/>
    <hostnames>
      <hostname name="test-server.local" type="PTR"/>
    </hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" reason="syn-ack"/>
        <service name="ssh" product="OpenSSH" version="8.9p1"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="nginx" version="1.18.0"/>
      </port>
    </ports>
    <os>
      <osmatch name="Linux 5.15" accuracy="95"/>
    </os>
  </host>
</nmaprun>"""


@pytest.fixture
def mock_nmap_runner(mocker):
    """
    Create a mocked nmap runner for testing without actual network scans.
    
    Args:
        mocker: Pytest-mock mocker fixture
        
    Returns:
        Mock: Mocked NMapRunner instance
    """
    from app.scanner.nmap_runner import NMapRunner
    
    mock = mocker.Mock(spec=NMapRunner)
    mock.discover_hosts.return_value = ("/tmp/scan.xml", ["192.168.1.100", "192.168.1.101"])
    mock.run_host_scan.return_value = "/tmp/host_scan.xml"
    
    return mock


@pytest.fixture
def api_client():
    """
    Create a test client for API endpoint testing.
    
    Returns:
        TestClient: FastAPI test client
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    
    # Override database dependency with test database  
    engine = create_engine(
        "sqlite:///file:test_api_db?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create default admin user for tests
    from app.models import User, UserRole
    from app.auth import get_password_hash
    
    db = TestSessionLocal()
    try:
        admin_user = User(
            username="admin",
            email="admin@localhost",
            full_name="Administrator",
            hashed_password=get_password_hash("Admin123!"),
            role=UserRole.ADMIN,
            must_change_password=False,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
    finally:
        db.close()
    
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    try:
        yield client
    finally:
        # Clean up
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
