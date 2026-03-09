"""
Nexus Mail — Application Configuration
Loaded from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration — all values loaded from .env file."""

    # --- App ---
    app_name: str = "NexusMail"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = Field(..., min_length=32)
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # --- MongoDB ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "nexus_mail"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Google OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # --- Google OAuth Scopes (single consent screen) ---
    @property
    def google_oauth_scopes(self) -> List[str]:
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ]

    # --- Google Calendar ---
    calendar_api_version: str = "v3"
    calendar_business_hours_start: int = 9
    calendar_business_hours_end: int = 18

    # --- AI Providers ---
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    ai_provider: str = "groq"  # "groq" | "openrouter"
    ai_model: str = "llama-3.3-70b-versatile"

    # --- Meeting Intelligence ---
    meeting_detection_confidence_threshold: float = 0.75
    suggested_slots_count: int = 3

    # --- Notification ---
    notification_poll_interval_seconds: int = 60

    # --- Security / JWT ---
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    encryption_key: str = ""  # AES-256 key, base64 encoded

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
