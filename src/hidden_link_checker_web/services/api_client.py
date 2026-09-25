"""HTTP-only client for the API module."""

from collections.abc import Mapping
from uuid import UUID

import httpx

from hidden_link_checker_web.config import WebSettings
from shared_contracts.api_models import (
    CurrentUserResponse,
    LinkCheckHistoryItem,
    LinkCheckResponse,
)


class HiddenLinkCheckerApiClient:
    """Call the API without accessing persistence or domain internals."""

    def __init__(
        self, settings: WebSettings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base_url = settings.api_base_url.rstrip("/")
        self._transport = transport

    def _client(self, cookies: Mapping[str, str]) -> httpx.AsyncClient:
        """Create an API-only client and optionally inject a test transport."""
        return httpx.AsyncClient(
            base_url=self._base_url,
            cookies=cookies,
            transport=self._transport,
        )

    async def create_link_check(
        self, url: str, cookies: Mapping[str, str]
    ) -> LinkCheckResponse:
        """Inspect one URL synchronously using the browser's API session cookie."""
        async with self._client(cookies) as client:
            response = await client.post("/v1/link-checks", json={"url": url})
        response.raise_for_status()
        return LinkCheckResponse.model_validate(response.json())

    async def list_link_checks(self, cookies: Mapping[str, str]) -> list[LinkCheckHistoryItem]:
        """Load history visible to the current user."""
        async with self._client(cookies) as client:
            response = await client.get("/v1/me/link-checks")
        response.raise_for_status()
        return [LinkCheckHistoryItem.model_validate(item) for item in response.json()]

    async def delete_link_check(self, check_id: UUID, cookies: Mapping[str, str]) -> None:
        """Delete one owned URL history item through the API."""
        async with self._client(cookies) as client:
            response = await client.delete(f"/v1/me/link-checks/{check_id}")
        response.raise_for_status()

    async def get_current_user(self, cookies: Mapping[str, str]) -> CurrentUserResponse:
        """Return the profile resolved by the API from the session cookie."""
        async with self._client(cookies) as client:
            response = await client.get("/v1/me")
        response.raise_for_status()
        return CurrentUserResponse.model_validate(response.json())

    async def logout(self, cookies: Mapping[str, str]) -> None:
        """Ask the API to revoke the server-side session."""
        async with self._client(cookies) as client:
            response = await client.post("/v1/auth/logout")
        response.raise_for_status()

    def google_login_url(self) -> str:
        """Return the API endpoint that begins the Google OIDC redirect flow."""
        return f"{self._base_url}/v1/auth/google/start"
