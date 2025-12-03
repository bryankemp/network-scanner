"""
Artifact model for storing generated scan files.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class ArtifactType(str, enum.Enum):
    """Artifact type enumeration."""

    HTML = "html"
    PNG = "png"
    SVG = "svg"
    XLSX = "xlsx"
    DOT = "dot"
    XML = "xml"


class Artifact(Base):
    """Artifact model for scan output files."""

    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ArtifactType), nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Foreign keys
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)

    # Relationships
    scan = relationship("Scan", back_populates="artifacts")

    def __repr__(self):
        return f"<Artifact(type='{self.type}', path='{self.file_path}')>"
