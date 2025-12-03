"""
Pydantic schemas for statistics.
"""

from pydantic import BaseModel


class NetworkStats(BaseModel):
    """Network statistics response."""

    total_scans: int
    total_hosts: int
    total_vms: int
    total_services: int
    recent_scans: int  # Scans in last 24 hours
    active_schedules: int
    failed_scans: int
