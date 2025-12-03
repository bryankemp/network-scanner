"""
Pydantic schemas for Settings API endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    """Application settings."""

    scan_parallelism: int = Field(
        default=8, ge=1, le=32, description="Number of concurrent host scans (1-32)"
    )
    data_retention_days: int = Field(
        default=90, ge=1, le=365, description="Number of days to retain scan data (1-365)"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"scan_parallelism": 8, "data_retention_days": 90}},
    )


class AppSettingsResponse(AppSettings):
    """Response schema for settings."""

    pass
