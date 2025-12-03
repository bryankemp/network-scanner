"""
Host model for discovered network devices.

This module defines the Host model representing individual devices discovered
during network scans, including their properties, services, and scan status.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class HostScanStatus(str, enum.Enum):
    """Enumeration of per-host scan statuses.

    Attributes:
        PENDING: Host discovered but not yet scanned in detail
        SCANNING: Detailed host scan currently in progress
        COMPLETED: Host scan completed successfully
        FAILED: Host scan failed or timed out
    """

    PENDING = "pending"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"


class Host(Base):
    """SQLAlchemy model for discovered network devices.

    Represents a single host/device discovered during a network scan,
    including its network properties, OS information, VM detection,
    and per-host scan progress tracking.

    Attributes:
        id: Primary key identifier
        ip: IPv4 address of the host
        hostname: DNS hostname (if resolved)
        mac: MAC address (requires host networking mode)
        vendor: Hardware vendor from MAC OUI lookup
        os: Operating system detected by nmap
        is_vm: Whether this host is a virtual machine/container
        vm_type: Type of virtualization (VMware, Docker, VirtualBox, etc.)
        physical_host_ip: IP of physical host if this is a VM
        os_accuracy: OS detection confidence score (0-100)
        uptime_seconds: How long the host has been running
        last_boot: Estimated last boot timestamp
        distance: Network distance in hops from scanner
        cpe: Common Platform Enumeration identifier
        scan_status: Current status of this host's detailed scan
        scan_started_at: When this host's scan began
        scan_completed_at: When this host's scan finished
        scan_progress_percent: Scan progress for this host (0-100)
        scan_error_message: Error message if scan failed
        ports_discovered: Number of open ports found
        scan_id: Foreign key to parent Scan
        scan: Relationship to parent Scan
        ports: Relationship to Port records (open services)
        traceroute_hops: Relationship to TracerouteHop records

    Example:
        >>> host = Host(ip="192.168.1.100", hostname="server.local", scan_id=1)
        >>> db.add(host)
        >>> db.commit()
    """

    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False, index=True)
    hostname = Column(String, nullable=True)
    mac = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # VM/Container detection
    is_vm = Column(Boolean, default=False)
    vm_type = Column(String, nullable=True)  # e.g., "VMware", "VirtualBox", "Docker"
    physical_host_ip = Column(
        String, nullable=True
    )  # IP of physical host if this is a VM/container

    # Additional nmap data
    os_accuracy = Column(Integer, nullable=True)  # OS detection confidence (0-100)
    uptime_seconds = Column(Integer, nullable=True)  # How long host has been up
    last_boot = Column(String, nullable=True)  # Estimated last boot time
    distance = Column(Integer, nullable=True)  # Network distance (hops)
    cpe = Column(String, nullable=True)  # Common Platform Enumeration

    # Scan progress tracking
    scan_status = Column(SQLEnum(HostScanStatus), default=HostScanStatus.PENDING, nullable=False)
    scan_started_at = Column(DateTime, nullable=True)
    scan_completed_at = Column(DateTime, nullable=True)
    scan_progress_percent = Column(Integer, default=0, nullable=False)
    scan_error_message = Column(String, nullable=True)
    ports_discovered = Column(Integer, default=0, nullable=False)

    # Foreign keys
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)

    # Relationships
    scan = relationship("Scan", back_populates="hosts")
    ports = relationship("Port", back_populates="host", cascade="all, delete-orphan")
    traceroute_hops = relationship(
        "TracerouteHop", back_populates="host", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Host(ip='{self.ip}', hostname='{self.hostname}', is_vm={self.is_vm})>"
