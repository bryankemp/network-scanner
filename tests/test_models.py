"""
Unit tests for SQLAlchemy models.

Tests all database models including Scan, Host, Port, Artifact,
and their relationships, enums, and constraints.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models import (
    Scan, Host, Port, Artifact,
    ScanStatus, HostScanStatus, ArtifactType
)


class TestScanModel:
    """Test suite for the Scan model."""
    
    def test_create_scan(self, db_session):
        """Test creating a basic scan record."""
        scan = Scan(network_range="192.168.1.0/24", status=ScanStatus.PENDING)
        db_session.add(scan)
        db_session.commit()
        
        assert scan.id is not None
        assert scan.network_range == "192.168.1.0/24"
        assert scan.status == ScanStatus.PENDING
        assert scan.progress_percent == 0
        assert scan.created_at is not None
    
    def test_scan_status_enum(self):
        """Test ScanStatus enum values."""
        assert ScanStatus.PENDING.value == "pending"
        assert ScanStatus.RUNNING.value == "running"
        assert ScanStatus.COMPLETED.value == "completed"
        assert ScanStatus.FAILED.value == "failed"
        assert ScanStatus.CANCELLED.value == "cancelled"
    
    def test_scan_progress_tracking(self, db_session):
        """Test scan progress updates."""
        scan = Scan(network_range="10.0.0.0/24", status=ScanStatus.RUNNING)
        scan.progress_percent = 75
        scan.progress_message = "Scanning hosts..."
        
        db_session.add(scan)
        db_session.commit()
        
        assert scan.progress_percent == 75
        assert scan.progress_message == "Scanning hosts..."
    
    def test_scan_with_error(self, db_session):
        """Test scan with error message."""
        scan = Scan(
            network_range="172.16.0.0/16",
            status=ScanStatus.FAILED,
            error_message="Network unreachable"
        )
        db_session.add(scan)
        db_session.commit()
        
        assert scan.status == ScanStatus.FAILED
        assert scan.error_message == "Network unreachable"
    
    def test_scan_repr(self, db_session):
        """Test scan string representation."""
        scan = Scan(network_range="192.168.1.0/24", status=ScanStatus.RUNNING)
        db_session.add(scan)
        db_session.commit()
        
        repr_str = repr(scan)
        assert "Scan" in repr_str
        assert "192.168.1.0/24" in repr_str
        # Status shows as enum repr: ScanStatus.RUNNING
        assert "RUNNING" in repr_str or "running" in repr_str


class TestHostModel:
    """Test suite for the Host model."""
    
    def test_create_host(self, db_session, sample_scan):
        """Test creating a host record."""
        host = Host(
            ip="192.168.1.50",
            hostname="web-server",
            scan_id=sample_scan.id
        )
        db_session.add(host)
        db_session.commit()
        
        assert host.id is not None
        assert host.ip == "192.168.1.50"
        assert host.hostname == "web-server"
        assert host.scan_id == sample_scan.id
    
    def test_host_with_os_detection(self, db_session, sample_scan):
        """Test host with OS information."""
        host = Host(
            ip="192.168.1.100",
            os="Ubuntu 22.04",
            os_accuracy=98,
            scan_id=sample_scan.id
        )
        db_session.add(host)
        db_session.commit()
        
        assert host.os == "Ubuntu 22.04"
        assert host.os_accuracy == 98
    
    def test_host_vm_detection(self, db_session, sample_scan):
        """Test VM detection fields."""
        host = Host(
            ip="192.168.1.200",
            is_vm=True,
            vm_type="VMware",
            scan_id=sample_scan.id
        )
        db_session.add(host)
        db_session.commit()
        
        assert host.is_vm is True
        assert host.vm_type == "VMware"
    
    def test_host_scan_status(self, db_session, sample_scan):
        """Test host scan status tracking."""
        host = Host(
            ip="192.168.1.75",
            scan_status=HostScanStatus.SCANNING,
            scan_started_at=datetime.utcnow(),
            scan_progress_percent=50,
            scan_id=sample_scan.id
        )
        db_session.add(host)
        db_session.commit()
        
        assert host.scan_status == HostScanStatus.SCANNING
        assert host.scan_progress_percent == 50
        assert host.scan_started_at is not None
    
    def test_host_requires_scan_id(self, db_session):
        """Test that host requires a scan_id."""
        host = Host(ip="192.168.1.1")
        db_session.add(host)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_host_repr(self, db_session, sample_scan):
        """Test host string representation."""
        host = Host(
            ip="192.168.1.25",
            hostname="test-host",
            is_vm=True,
            scan_id=sample_scan.id
        )
        db_session.add(host)
        db_session.commit()
        
        repr_str = repr(host)
        assert "Host" in repr_str
        assert "192.168.1.25" in repr_str
        assert "test-host" in repr_str


class TestPortModel:
    """Test suite for the Port model."""
    
    def test_create_port(self, db_session, sample_host):
        """Test creating a port record."""
        port = Port(
            port=443,
            protocol="tcp",
            service="https",
            host_id=sample_host.id
        )
        db_session.add(port)
        db_session.commit()
        
        assert port.id is not None
        assert port.port == 443
        assert port.protocol == "tcp"
        assert port.service == "https"
    
    def test_port_with_service_details(self, db_session, sample_host):
        """Test port with detailed service information."""
        port = Port(
            port=3306,
            protocol="tcp",
            service="mysql",
            product="MySQL",
            version="8.0.32",
            extrainfo="protocol 10",
            host_id=sample_host.id
        )
        db_session.add(port)
        db_session.commit()
        
        assert port.service == "mysql"
        assert port.product == "MySQL"
        assert port.version == "8.0.32"
        assert port.extrainfo == "protocol 10"
    
    def test_port_requires_host_id(self, db_session):
        """Test that port requires a host_id."""
        port = Port(port=80, protocol="tcp")
        db_session.add(port)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestArtifactModel:
    """Test suite for the Artifact model."""
    
    def test_create_artifact(self, db_session, sample_scan):
        """Test creating an artifact record."""
        artifact = Artifact(
            type=ArtifactType.HTML,
            file_path="/tmp/scan_1.html",
            scan_id=sample_scan.id
        )
        db_session.add(artifact)
        db_session.commit()
        
        assert artifact.id is not None
        assert artifact.type == ArtifactType.HTML
        assert artifact.file_path == "/tmp/scan_1.html"
        # Artifact model doesn't have created_at field
    
    def test_artifact_types(self):
        """Test ArtifactType enum values."""
        assert ArtifactType.HTML.value == "html"
        assert ArtifactType.XLSX.value == "xlsx"
        assert ArtifactType.XML.value == "xml"
        assert ArtifactType.PNG.value == "png"


class TestRelationships:
    """Test suite for model relationships."""
    
    def test_scan_hosts_relationship(self, db_session, sample_scan):
        """Test Scan -> Hosts relationship."""
        host1 = Host(ip="192.168.1.1", scan_id=sample_scan.id)
        host2 = Host(ip="192.168.1.2", scan_id=sample_scan.id)
        
        db_session.add_all([host1, host2])
        db_session.commit()
        
        db_session.refresh(sample_scan)
        assert len(sample_scan.hosts) == 2
        assert host1 in sample_scan.hosts
        assert host2 in sample_scan.hosts
    
    def test_host_ports_relationship(self, db_session, sample_host):
        """Test Host -> Ports relationship."""
        port1 = Port(port=22, protocol="tcp", service="ssh", host_id=sample_host.id)
        port2 = Port(port=80, protocol="tcp", service="http", host_id=sample_host.id)
        
        db_session.add_all([port1, port2])
        db_session.commit()
        
        db_session.refresh(sample_host)
        assert len(sample_host.ports) == 2
    
    def test_cascade_delete_scan(self, db_session, sample_scan):
        """Test that deleting a scan cascades to hosts."""
        host = Host(ip="192.168.1.1", scan_id=sample_scan.id)
        db_session.add(host)
        db_session.commit()
        
        host_id = host.id
        
        db_session.delete(sample_scan)
        db_session.commit()
        
        # Host should be deleted via cascade
        deleted_host = db_session.query(Host).filter(Host.id == host_id).first()
        assert deleted_host is None
    
    def test_cascade_delete_host(self, db_session, sample_host):
        """Test that deleting a host cascades to ports."""
        port = Port(port=443, protocol="tcp", service="https", host_id=sample_host.id)
        db_session.add(port)
        db_session.commit()
        
        port_id = port.id
        
        db_session.delete(sample_host)
        db_session.commit()
        
        # Port should be deleted via cascade
        deleted_port = db_session.query(Port).filter(Port.id == port_id).first()
        assert deleted_port is None
