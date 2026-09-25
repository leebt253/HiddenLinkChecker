"""Configuration for the API process."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from hidden_link_checker_api.scan_limits import (
    DEFAULT_SCAN_MAX_CONCURRENT,
    DEFAULT_SCAN_MAX_REDIRECTS,
    DEFAULT_SCAN_MAX_RESPONSE_BYTES,
    DEFAULT_SCAN_TIMEOUT_SECONDS,
)


class ApiSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HIDDEN_LINK_CHECKER_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "production"
    database_url: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    web_base_url: str = "http://127.0.0.1:8001"
    session_cookie_name: str = "hidden_link_checker_session"
    session_lifetime_days: int = 7
    session_cookie_secure: bool = False
    scan_timeout_seconds: float = DEFAULT_SCAN_TIMEOUT_SECONDS
    scan_max_redirects: int = DEFAULT_SCAN_MAX_REDIRECTS
    scan_max_response_bytes: int = DEFAULT_SCAN_MAX_RESPONSE_BYTES
    scan_max_concurrent: int = DEFAULT_SCAN_MAX_CONCURRENT
    browser_executable_path: str | None = None
