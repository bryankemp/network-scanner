"""
Scan model for network scanning operations.

This module defines the Scan model for tracking network scan operations,
including status, progress, and relationships to discovered hosts and artifacts.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database import Base


class ScanStatus(str, enum.Enum):
    """Enumeration of possible scan statuses.

    Attributes:
        PENDING: Scan is queued but not yet started
        RUNNING: Scan is currently in progress
        COMPLETED: Scan finished successfully
        FAILED: Scan failed with an error
        CANCELLED: Scan was cancelled by user
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scan(Base):
    """SQLAlchemy model for network scan operations.

    Tracks the lifecycle of a network scan including status, progress,
    timing information, and relationships to discovered hosts and generated artifacts.

    Attributes:
        id: Primary key identifier
        network_range: CIDR notation network range(s) to scan (e.g., "192.168.1.0/24")
        status: Current status of the scan (ScanStatus enum)
        started_at: Timestamp when scan execution began
        completed_at: Timestamp when scan finished (success or failure)
        created_at: Timestamp when scan was created/queued
        progress_percent: Scan progress from 0-100
        progress_message: Human-readable progress status message
        error_message: Error details if scan failed
        schedule_id: Foreign key to ScanSchedule if this is a scheduled scan
        schedule: Relationship to ScanSchedule
        hosts: Relationship to all Host records discovered in this scan
        artifacts: Relationship to all Artifact files generated (HTML, Excel, etc.)

    Example:
        >>> scan = Scan(network_range="192.168.1.0/24", status=ScanStatus.PENDING)
        >>> db.add(scan)
        >>> db.commit()
    """

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    network_range = Column(String, nullable=False)
    status = Column(Enum(ScanStatus), nullable=False, default=ScanStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Progress tracking
    progress_percent = Column(Integer, default=0)
    progress_message = Column(String, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # Foreign keys
    schedule_id = Column(Integer, ForeignKey("scan_schedules.id"), nullable=True)

    # Relationships
    schedule = relationship("ScanSchedule", back_populates="scans")
    hosts = relationship("Host", back_populates="scan", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan(id={self.id}, range='{self.network_range}', status='{self.status}')>"
