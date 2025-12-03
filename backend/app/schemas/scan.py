"""
Pydantic schemas for scans and hosts.
"""

from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List
import ipaddress


# Port schemas
class PortResponse(BaseModel):
    """Port response schema."""

    id: int
    port: int
    protocol: str
    service: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    extrainfo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Host schemas
class HostResponse(BaseModel):
    """Host response schema."""

    id: int
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    vendor: Optional[str] = None
    os: Optional[str] = None
    is_vm: bool
    vm_type: Optional[str] = None
    physical_host_ip: Optional[str] = None

    # Scan progress tracking
    scan_status: str
    scan_started_at: Optional[datetime] = None
    scan_completed_at: Optional[datetime] = None
    scan_progress_percent: int = 0
    scan_error_message: Optional[str] = None
    ports_discovered: int = 0

    ports: list[PortResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Artifact schemas
class ArtifactResponse(BaseModel):
    """Artifact response schema."""

    id: int
    type: str
    file_path: str
    file_size: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Scan schemas
class ScanCreate(BaseModel):
    """Scan creation schema."""

    networks: Optional[List[str]] = None

    @field_validator("networks")
    @classmethod
    def validate_networks(cls, v):
        """Validate that all networks are valid CIDR notation."""
        # None is allowed - will auto-detect
        if v is None:
            return v

        # Empty list not allowed
        if v == []:
            raise ValueError(
                "If networks are specified, at least one network must be provided. Omit the field to auto-detect."
            )

        for network in v:
            try:
                ipaddress.ip_network(network, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid CIDR network '{network}': {e}")

        return v


class ScanResponse(BaseModel):
    """Scan response schema."""

    id: int
    network_range: str  # Stored as comma-separated for display
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    progress_percent: int
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    schedule_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ScanDetailResponse(ScanResponse):
    """Detailed scan response with hosts and artifacts."""

    hosts: list[HostResponse] = []
    artifacts: list[ArtifactResponse] = []


class ScanListResponse(BaseModel):
    """Scan list response schema."""

    scans: list[ScanResponse]
    total: int
    page: int
    page_size: int


# WebSocket message schemas
class ScanProgressMessage(BaseModel):
    """WebSocket scan progress message."""

    scan_id: int
    status: str
    progress_percent: int
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
