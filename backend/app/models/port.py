"""
Port model for open ports and services on hosts.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class Port(Base):
    """Port model for open ports and services."""

    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, index=True)
    port = Column(Integer, nullable=False)
    protocol = Column(String, nullable=False)  # tcp, udp
    service = Column(String, nullable=True)
    product = Column(String, nullable=True)
    version = Column(String, nullable=True)
    extrainfo = Column(String, nullable=True)
    cpe = Column(String, nullable=True)  # Common Platform Enumeration for service
    script_output = Column(String, nullable=True)  # NSE script results (JSON)

    # Foreign keys
    host_id = Column(Integer, ForeignKey("hosts.id"), nullable=False)

    # Relationships
    host = relationship("Host", back_populates="ports")

    def __repr__(self):
        return f"<Port(port={self.port}, protocol='{self.protocol}', service='{self.service}')>"
