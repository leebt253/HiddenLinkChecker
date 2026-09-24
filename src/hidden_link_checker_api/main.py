"""Application factory for the API module."""

from datetime import timedelta

from fastapi import FastAPI

from hidden_link_checker_api.config import ApiSettings
from hidden_link_checker_api.controllers.auth import router as auth_router
from hidden_link_checker_api.controllers.link_checks import router as link_checks_router
from hidden_link_checker_api.repositories.auth import (
    AuthRepository,
    InMemoryAuthRepository,
    PostgreSQLAuthRepository,
)
from hidden_link_checker_api.repositories.link_checks import (
    InMemoryLinkCheckRepository,
    LinkCheckRepository,
    PostgreSQLLinkCheckRepository,
)
from hidden_link_checker_api.services.auth import (
    AuthenticationService,
    GoogleIdTokenVerifier,
    GoogleOAuthClient,
)
from hidden_link_checker_api.services.link_checks import LinkCheckService
from hidden_link_checker_api.workers.link_check_worker import LinkCheckWorker
from hidden_link_checker_api.workers.queue import InMemoryLinkCheckQueue


def create_app(settings: ApiSettings | None = None, auth_repository: AuthRepository | None = None) -> FastAPI:
    """Create the API application with replaceable infrastructure adapters."""
    resolved_settings = settings or ApiSettings()
    app = FastAPI(title="Hidden Link Checker API", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.authentication_service = _build_authentication_service(resolved_settings, auth_repository)
    link_check_repository: LinkCheckRepository = (
        PostgreSQLLinkCheckRepository(resolved_settings.database_url)
        if resolved_settings.database_url
        else InMemoryLinkCheckRepository()
    )
    link_check_worker = LinkCheckWorker(
        link_check_repository,
        timeout_seconds=resolved_settings.scan_timeout_seconds,
        max_redirects=resolved_settings.scan_max_redirects,
        max_response_bytes=resolved_settings.scan_max_response_bytes,
    )
    app.state.link_check_service = LinkCheckService(
        repository=link_check_repository,
        queue=InMemoryLinkCheckQueue(
            link_check_worker.process, max_concurrent=resolved_settings.scan_max_concurrent
        ),
    )
    app.include_router(auth_router)
    app.include_router(link_checks_router)
    return app


def _build_authentication_service(
    settings: ApiSettings, repository: AuthRepository | None
) -> AuthenticationService | None:
    if not _google_credentials_are_configured(settings):
        return None
    resolved_repository = repository or _default_auth_repository(settings)
    return AuthenticationService(
        repository=resolved_repository,
        oauth_client=GoogleOAuthClient(settings),
        verifier=GoogleIdTokenVerifier(settings.google_client_id or ""),
        session_lifetime=timedelta(days=settings.session_lifetime_days),
        transaction_lifetime=timedelta(minutes=10),
    )


def _default_auth_repository(settings: ApiSettings) -> AuthRepository:
    if settings.database_url:
        return PostgreSQLAuthRepository(settings.database_url)
    return InMemoryAuthRepository()


def _google_credentials_are_configured(settings: ApiSettings) -> bool:
    return all(_is_configured_google_setting(value) for value in (
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_redirect_uri,
    ))


def _is_configured_google_setting(value: str | None) -> bool:
    return bool(value and not value.startswith("replace-with-"))


app = create_app()
