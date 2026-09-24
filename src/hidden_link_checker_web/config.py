"""Configuration for the web process."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Runtime configuration for the API-driven web module."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HIDDEN_LINK_CHECKER_",
        extra="ignore",
    )

    web_host: str = "127.0.0.1"
    web_port: int = 8001
    api_base_url: str = "http://127.0.0.1:8000"
    session_cookie_name: str = "hidden_link_checker_session"
