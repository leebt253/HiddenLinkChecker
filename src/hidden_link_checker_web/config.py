"""Configuration for the web process."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Runtime configuration for the API-driven web module."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HIDDEN_LINK_CHECKER_",
        extra="ignore",
    )

    api_base_url: str = "http://127.0.0.1:8000"
    session_cookie_name: str = "hidden_link_checker_session"
