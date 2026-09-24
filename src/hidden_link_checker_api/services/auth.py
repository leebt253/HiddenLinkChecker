"""Google OpenID Connect and server-side session application services."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Protocol
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from hidden_link_checker_api.config import ApiSettings
from hidden_link_checker_api.domain.models import (
    GoogleIdentity,
    OAuthLoginTransaction,
    User,
    UserSession,
)
from hidden_link_checker_api.repositories.auth import AuthRepository

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class InvalidOAuthCallbackError(ValueError):
    """Raised when Google callback data cannot establish a trusted identity."""


class IdTokenVerifier(Protocol):
    """Verifies a Google ID token and returns only the identity claims we retain."""

    def verify(self, raw_id_token: str, expected_nonce_hash: bytes) -> GoogleIdentity:
        """Validate token signature, issuer, audience and nonce."""


class GoogleIdTokenVerifier:
    """Google ID-token verifier backed by Google's certificate discovery."""

    def __init__(self, client_id: str) -> None:
        self._client_id = client_id

    def verify(self, raw_id_token: str, expected_nonce_hash: bytes) -> GoogleIdentity:
        try:
            claims = id_token.verify_oauth2_token(raw_id_token, GoogleRequest(), self._client_id)
        except ValueError as error:
            raise InvalidOAuthCallbackError("The Google ID token is invalid.") from error
        if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
            raise InvalidOAuthCallbackError("The Google ID token issuer is invalid.")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or OAuthLoginTransaction.hash_value(nonce) != expected_nonce_hash:
            raise InvalidOAuthCallbackError("The Google ID token nonce is invalid.")
        if not claims.get("email_verified"):
            raise InvalidOAuthCallbackError("The Google account email is not verified.")
        subject = claims.get("sub")
        email = claims.get("email")
        if not isinstance(subject, str) or not isinstance(email, str):
            raise InvalidOAuthCallbackError("The Google ID token identity is incomplete.")
        return GoogleIdentity(
            subject=subject, email=email, display_name=_optional_claim(claims, "name"),
            avatar_url=_optional_claim(claims, "picture"),
        )


class GoogleOAuthClient:
    """Build authorization requests and exchange callback codes over TLS."""

    def __init__(self, settings: ApiSettings) -> None:
        self._client_id = _required_setting(settings.google_client_id, "GOOGLE_CLIENT_ID")
        self._client_secret = _required_setting(settings.google_client_secret, "GOOGLE_CLIENT_SECRET")
        self._redirect_uri = _required_setting(settings.google_redirect_uri, "GOOGLE_REDIRECT_URI")

    def authorization_url(self, state: str, nonce: str) -> str:
        """Return Google's fixed authorization endpoint with OIDC safeguards."""
        query = urlencode({
            "client_id": self._client_id, "redirect_uri": self._redirect_uri, "response_type": "code",
            "scope": "openid email profile", "state": state, "nonce": nonce,
        })
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"

    async def exchange_code(self, code: str) -> str:
        """Exchange the short-lived authorization code and retain only its ID token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(GOOGLE_TOKEN_ENDPOINT, data={
                "code": code, "client_id": self._client_id, "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri, "grant_type": "authorization_code",
            })
        if response.status_code != 200:
            raise InvalidOAuthCallbackError("Google could not complete sign-in.")
        raw_id_token = response.json().get("id_token")
        if not isinstance(raw_id_token, str):
            raise InvalidOAuthCallbackError("Google did not return an ID token.")
        return raw_id_token


class AuthenticationService:
    """Coordinate one-time OIDC transactions, user persistence and session lifecycle."""

    def __init__(self, repository: AuthRepository, oauth_client: GoogleOAuthClient, verifier: IdTokenVerifier,
                 session_lifetime: timedelta, transaction_lifetime: timedelta) -> None:
        self._repository = repository
        self._oauth_client = oauth_client
        self._verifier = verifier
        self._session_lifetime = session_lifetime
        self._transaction_lifetime = transaction_lifetime

    def begin_google_login(self) -> str:
        """Persist state/nonce server-side and return the Google authorization URL."""
        now = _utc_now()
        state = token_urlsafe(32)
        nonce = token_urlsafe(32)
        self._repository.create_oauth_transaction(
            OAuthLoginTransaction.from_values(state, nonce, now + self._transaction_lifetime)
        )
        return self._oauth_client.authorization_url(state, nonce)

    async def complete_google_login(self, code: str, state: str) -> tuple[User, str]:
        """Consume a callback transaction, persist the user and issue an opaque session token."""
        now = _utc_now()
        transaction = self._repository.consume_oauth_transaction(state, now)
        if transaction is None:
            raise InvalidOAuthCallbackError("The Google sign-in request is invalid or expired.")
        raw_id_token = await self._oauth_client.exchange_code(code)
        identity = self._verifier.verify(raw_id_token, expected_nonce_hash=transaction.nonce_hash)
        user = self._repository.upsert_user(identity, now)
        session_token = token_urlsafe(48)
        self._repository.create_session(UserSession.from_token(session_token, user.id, now + self._session_lifetime))
        return user, session_token

    def get_user_from_session(self, session_token: str | None) -> User | None:
        """Resolve a current user from a browser cookie without accepting a user ID."""
        if not session_token:
            return None
        return self._repository.get_user_by_session_token(session_token, _utc_now())

    def logout(self, session_token: str | None) -> None:
        """Revoke an existing session, if supplied, without disclosing its validity."""
        if session_token:
            self._repository.revoke_session(session_token, _utc_now())


def _optional_claim(claims: dict[str, object], key: str) -> str | None:
    value = claims.get(key)
    return value if isinstance(value, str) else None


def _required_setting(value: str | None, name: str) -> str:
    if value:
        return value
    raise RuntimeError(f"{name} must be configured to enable Google sign-in.")


def _utc_now() -> datetime:
    return datetime.now(UTC)