"""Application factory for the API-driven web module."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from hidden_link_checker_web.config import WebSettings
from hidden_link_checker_web.controllers.auth import router as auth_router
from hidden_link_checker_web.controllers.dashboard import router as dashboard_router
from hidden_link_checker_web.services.api_client import HiddenLinkCheckerApiClient
from hidden_link_checker_web.views.pages import render_error


def create_app(settings: WebSettings | None = None) -> FastAPI:
    """Create a web application that only communicates with the API over HTTP."""
    resolved_settings = settings or WebSettings()
    app = FastAPI(title="Hidden Link Checker Web", version="0.1.0")
    app.state.api_client = HiddenLinkCheckerApiClient(resolved_settings)
    app.state.session_cookie_name = resolved_settings.session_cookie_name
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.add_exception_handler(404, _not_found_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)
    return app


async def _not_found_handler(request: Request, exception: Exception) -> HTMLResponse:
    """Render a branded page for routes that do not exist."""
    return HTMLResponse(render_error(404, "Page not found", "The page you requested does not exist."), 404)


async def _http_error_handler(request: Request, exception: HTTPException) -> HTMLResponse:
    """Render controlled application errors without returning FastAPI JSON."""
    message = exception.detail if isinstance(exception.detail, str) else "The request could not be completed."
    return HTMLResponse(render_error(exception.status_code, "Request could not be completed", message), exception.status_code)


async def _unexpected_error_handler(request: Request, exception: Exception) -> HTMLResponse:
    """Render a generic error without exposing the exception or stack trace."""
    return HTMLResponse(render_error(500, "Something went wrong", "Please try again in a moment."), 500)


app = create_app()
