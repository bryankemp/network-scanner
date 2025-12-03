"""
Pydantic schemas package.
"""

from .auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    PasswordResetRequest,
)
from .user import (
    UserCreate,
    UserResponse,
    UserListResponse,
    PasswordChangeRequest as UserPasswordChangeRequest,
    UserUpdate,
    PasswordResetRequest as UserPasswordResetRequest,
)
from .scan import (
    PortResponse,
    HostResponse,
    ArtifactResponse,
    ScanCreate,
    ScanResponse,
    ScanDetailResponse,
    ScanListResponse,
    ScanProgressMessage,
)
from .schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse
from .stats import NetworkStats

__all__ = [
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "PasswordResetRequest",
    # User
    "UserCreate",
    "UserResponse",
    "UserListResponse",
    "UserPasswordChangeRequest",
    "UserUpdate",
    "UserPasswordResetRequest",
    # Scan
    "PortResponse",
    "HostResponse",
    "ArtifactResponse",
    "ScanCreate",
    "ScanResponse",
    "ScanDetailResponse",
    "ScanListResponse",
    "ScanProgressMessage",
    # Schedule
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleListResponse",
    # Stats
    "NetworkStats",
]
