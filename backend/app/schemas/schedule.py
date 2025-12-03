"""
Pydantic schemas for scan schedules.
"""

from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional


class ScheduleCreate(BaseModel):
    """Schedule creation schema."""

    name: str
    cron_expression: str
    network_range: str
    enabled: bool = True

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression format."""
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError("Cron expression must have 5 or 6 parts")
        return v


class ScheduleUpdate(BaseModel):
    """Schedule update schema."""

    name: Optional[str] = None
    cron_expression: Optional[str] = None
    network_range: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format."""
        if v is not None:
            parts = v.split()
            if len(parts) not in [5, 6]:
                raise ValueError("Cron expression must have 5 or 6 parts")
        return v


class ScheduleResponse(BaseModel):
    """Schedule response schema."""

    id: int
    name: str
    cron_expression: str
    network_range: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_by_id: int

    model_config = ConfigDict(from_attributes=True)


class ScheduleListResponse(BaseModel):
    """Schedule list response schema."""

    schedules: list[ScheduleResponse]
    total: int
