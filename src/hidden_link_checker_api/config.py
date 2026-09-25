"""Configuration for the API process."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HIDDEN_LINK_CHECKER_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "production"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    web_base_url: str = "http://127.0.0.1:8001"
    session_cookie_name: str = "hidden_link_checker_session"
    session_lifetime_days: int = 7
    session_cookie_secure: bool = False
    scan_timeout_seconds: float = 10.0
    scan_max_redirects: int = 5
    scan_max_response_bytes: int = 2 * 1024 * 1024
    scan_max_concurrent: int = 4
    browser_executable_path: str | None = None
