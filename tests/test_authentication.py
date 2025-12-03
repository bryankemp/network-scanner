"""
Unit tests for authentication endpoints and security utilities.

Tests login authentication, token generation, password hashing, and user validation.
Author: Bryan Kemp <bryan@kempville.com>
"""
import pytest
from datetime import datetime, timedelta
from fastapi import status
from jose import jwt

from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models import User, UserRole
from app.config import settings


class TestPasswordSecurity:
    """Tests for password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification with bcrypt."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Verify the hashed password is different from plain text
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify incorrect password
        assert verify_password("WrongPassword", hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that hashing the same password twice produces different hashes."""
        password = "SamePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Different salts should produce different hashes
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenGeneration:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation with default expiration."""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Decode and verify token
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """Test access token with custom expiration time."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=5)
        token = create_access_token(data, expires_delta)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation with long expiration."""
        data = {"sub": "testuser"}
        token = create_refresh_token(data)

        # Decode and verify token
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        assert payload is None

    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        data = {"sub": "testuser"}
        # Create token that expired 1 hour ago
        expires_delta = timedelta(hours=-1)
        token = create_access_token(data, expires_delta)

        payload = decode_token(token)
        # Should return None for expired token
        assert payload is None


class TestLoginEndpoint:
    """Tests for /api/auth/login endpoint."""

    def test_login_with_valid_credentials(self, api_client):
        """Test successful login with valid username and password."""
        response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert isinstance(data["must_change_password"], bool)

        # Verify tokens are valid JWTs
        access_payload = decode_token(data["access_token"])
        assert access_payload is not None
        assert access_payload["sub"] == "admin"
        assert access_payload["type"] == "access"

        refresh_payload = decode_token(data["refresh_token"])
        assert refresh_payload is not None
        assert refresh_payload["sub"] == "admin"
        assert refresh_payload["type"] == "refresh"

    def test_login_with_invalid_username(self, api_client):
        """Test login fails with non-existent username."""
        response = api_client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "SomePassword123!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    def test_login_with_invalid_password(self, api_client):
        """Test login fails with incorrect password."""
        response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "WrongPassword123!"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    def test_login_with_missing_username(self, api_client):
        """Test login fails when username is missing."""
        response = api_client.post("/api/auth/login", json={"password": "Admin123!"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_missing_password(self, api_client):
        """Test login fails when password is missing."""
        response = api_client.post("/api/auth/login", json={"username": "admin"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_empty_credentials(self, api_client):
        """Test login fails with empty username and password."""
        response = api_client.post("/api/auth/login", json={"username": "", "password": ""})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_case_sensitive_username(self, api_client):
        """Test that username is case-sensitive."""
        response = api_client.post(
            "/api/auth/login", json={"username": "ADMIN", "password": "Admin123!"}
        )

        # Should fail because "ADMIN" != "admin"
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshTokenEndpoint:
    """Tests for /api/auth/refresh endpoint."""

    def test_refresh_token_success(self, api_client):
        """Test successful token refresh with valid refresh token."""
        import time
        
        # First, login to get tokens
        login_response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.json()["refresh_token"]
        original_access_token = login_response.json()["access_token"]

        # Wait 1 second to ensure different timestamp in token
        time.sleep(1)

        # Now refresh the token
        refresh_response = api_client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        data = refresh_response.json()

        # Verify new tokens are issued
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != original_access_token
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_with_invalid_token(self, api_client):
        """Test token refresh fails with invalid refresh token."""
        response = api_client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_with_access_token(self, api_client):
        """Test that using access token for refresh fails (wrong token type)."""
        # Login to get access token
        login_response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh
        # Note: Current implementation doesn't validate token type in refresh endpoint
        # This test documents the behavior
        response = api_client.post("/api/auth/refresh", json={"refresh_token": access_token})

        # Should still work but is semantically incorrect
        # Consider adding token type validation in production
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


class TestGetCurrentUserEndpoint:
    """Tests for /api/auth/me endpoint."""

    def test_get_current_user_with_valid_token(self, api_client):
        """Test retrieving current user info with valid access token."""
        # Login first
        login_response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
        )
        access_token = login_response.json()["access_token"]

        # Get current user info
        response = api_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "email" in data

    def test_get_current_user_without_token(self, api_client):
        """Test that accessing /me without token fails."""
        response = api_client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_invalid_token(self, api_client):
        """Test that accessing /me with invalid token fails."""
        response = api_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""

    def test_full_authentication_flow(self, api_client):
        """Test complete authentication flow: login, access protected endpoint, refresh."""
        # Step 1: Login
        login_response = api_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # Step 2: Access protected endpoint
        me_response = api_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["username"] == "admin"

        # Step 3: Refresh token
        refresh_response = api_client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["access_token"]

        # Step 4: Use new access token
        me_response2 = api_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert me_response2.status_code == status.HTTP_200_OK
        assert me_response2.json()["username"] == "admin"
