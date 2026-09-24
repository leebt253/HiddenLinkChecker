"""Application factory for the API-driven web module."""

from fastapi import FastAPI

from hidden_link_checker_web.config import WebSettings
from hidden_link_checker_web.controllers.auth import router as auth_router
from hidden_link_checker_web.controllers.dashboard import router as dashboard_router
from hidden_link_checker_web.services.api_client import HiddenLinkCheckerApiClient


def create_app(settings: WebSettings | None = None) -> FastAPI:
    """Create a web application that only communicates with the API over HTTP."""
    resolved_settings = settings or WebSettings()
    app = FastAPI(title="Hidden Link Checker Web", version="0.1.0")
    app.state.api_client = HiddenLinkCheckerApiClient(resolved_settings)
    app.state.session_cookie_name = resolved_settings.session_cookie_name
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    return app


app = create_app()
