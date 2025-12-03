"""
Unit tests for FastAPI endpoints.

Tests authentication, scans, schedules, users, and settings endpoints.
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, api_client):
        """Test basic health check endpoint."""
        response = api_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthenticationEndpoints:
    """Tests for authentication endpoints."""
    
    def test_login_success(self, api_client):
        """Test successful login."""
        # Default admin user should exist
        response = api_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin123!"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials."""
        response = api_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_missing_fields(self, api_client):
        """Test login with missing fields."""
        response = api_client.post(
            "/api/auth/login",
            json={"username": "admin"}
        )
        assert response.status_code == 422  # Unprocessable Entity


class TestScanEndpoints:
    """Tests for scan management endpoints."""
    
    def test_list_scans(self, api_client):
        """Test listing all scans."""
        response = api_client.get("/api/scans")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
    
    def test_get_scan_not_found(self, api_client):
        """Test retrieving non-existent scan."""
        response = api_client.get("/api/scans/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_create_scan_requires_auth(self, api_client):
        """Test that creating scan requires authentication."""
        response = api_client.post(
            "/api/scans",
            json={"networks": ["192.168.1.0/24"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestScheduleEndpoints:
    """Tests for schedule management endpoints."""
    
    def test_list_schedules(self, api_client):
        """Test listing all schedules."""
        response = api_client.get("/api/schedules")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "schedules" in data
        assert "total" in data
    
    def test_get_schedule_not_found(self, api_client):
        """Test retrieving non-existent schedule."""
        response = api_client.get("/api/schedules/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStatsEndpoint:
    """Tests for statistics endpoint."""
    
    def test_get_stats(self, api_client):
        """Test retrieving network statistics."""
        response = api_client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_scans" in data
        assert "total_hosts" in data
        assert "total_vms" in data


class TestUserEndpoints:
    """Tests for user management endpoints (admin only)."""
    
    def test_list_users_requires_auth(self, api_client):
        """Test that listing users requires authentication."""
        response = api_client.get("/api/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_user_requires_auth(self, api_client):
        """Test that creating users requires authentication."""
        response = api_client.post(
            "/api/users",
            json={
                "username": "testuser",
                "password": "TestPass123!",
                "role": "USER"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSettingsEndpoints:
    """Tests for application settings endpoints."""
    
    def test_get_settings(self, api_client):
        """Test retrieving application settings."""
        response = api_client.get("/api/settings")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data_retention_days" in data
        assert "scan_parallelism" in data
