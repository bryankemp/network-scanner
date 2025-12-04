"""
Configuration settings for the network scanner backend.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Network Scanner API"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./data/database/network_scanner.db"

    # Security
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Scan Configuration
    scan_output_dir: str = "./scan_outputs"
    default_scan_timeout: int = 3600  # 1 hour in seconds
    scan_parallelism: int = 8  # number of concurrent host scans

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Admin defaults
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global settings instance
settings = Settings()

# Ensure scan output directory exists
os.makedirs(settings.scan_output_dir, exist_ok=True)
