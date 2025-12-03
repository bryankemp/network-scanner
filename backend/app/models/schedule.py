"""
Scan schedule model for recurring scans.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class ScanSchedule(Base):
    """Scan schedule model for cron-based recurring scans."""

    __tablename__ = "scan_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)  # e.g., "0 2 * * *" for daily at 2 AM
    network_range = Column(String, nullable=False)  # e.g., "192.168.1.0/24"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Foreign keys
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    created_by_user = relationship("User", back_populates="scan_schedules")
    scans = relationship("Scan", back_populates="schedule")

    def __repr__(self):
        return f"<ScanSchedule(name='{self.name}', cron='{self.cron_expression}', enabled={self.enabled})>"
