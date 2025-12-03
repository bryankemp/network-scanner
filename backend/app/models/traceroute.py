"""
Traceroute model for network path information.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship

from ..database import Base


class TracerouteHop(Base):
    """Traceroute hop model for network topology."""

    __tablename__ = "traceroute_hops"

    id = Column(Integer, primary_key=True, index=True)
    hop_number = Column(Integer, nullable=False)  # TTL/hop count
    ip = Column(String, nullable=True)  # IP of this hop
    hostname = Column(String, nullable=True)  # Hostname of this hop
    rtt = Column(Float, nullable=True)  # Round trip time in ms

    # Foreign keys
    host_id = Column(Integer, ForeignKey("hosts.id"), nullable=False)

    # Relationships
    host = relationship("Host", back_populates="traceroute_hops")

    def __repr__(self):
        return f"<TracerouteHop(hop={self.hop_number}, ip='{self.ip}')>"
