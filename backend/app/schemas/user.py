"""
Pydantic schemas for users.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
import re


class UserBase(BaseModel):
    """Base user schema."""

    username: str


class UserCreate(UserBase):
    """User creation schema."""

    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    password: str = Field(..., min_length=8, description="Password")
    role: str = Field(..., description="User role (ADMIN or USER)")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v):
        """Validate password complexity requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        if v.upper() not in ["ADMIN", "USER"]:
            raise ValueError("Role must be either ADMIN or USER")
        return v.upper()


class UserResponse(UserBase):
    """User response schema."""

    id: int
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """User list response schema."""

    users: list[UserResponse]
    total: int


class PasswordChangeRequest(BaseModel):
    """Request schema for password change."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v):
        """Validate password complexity requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[str] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    role: Optional[str] = Field(None, description="User role (ADMIN or USER)")
    is_active: Optional[bool] = Field(None, description="Account active status")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        if v is not None and v.upper() not in ["ADMIN", "USER"]:
            raise ValueError("Role must be either ADMIN or USER")
        return v.upper() if v else v


class PasswordResetRequest(BaseModel):
    """Request schema for admin password reset."""

    new_password: str = Field(..., min_length=8, description="New password")
    force_change: bool = Field(True, description="Force user to change password on next login")
