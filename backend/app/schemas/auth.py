"""
Pydantic schemas for authentication.
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False
    role: str
    username: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    """Admin password reset request schema."""

    new_password: str
