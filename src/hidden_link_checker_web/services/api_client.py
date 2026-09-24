"""HTTP-only client for the API module."""

from collections.abc import Mapping
from uuid import UUID

import httpx

from hidden_link_checker_web.config import WebSettings
from shared_contracts.api_models import (
    CreateLinkCheckResponse,
    CurrentUserResponse,
    LinkCheckHistoryItem,
    LinkCheckResponse,
)


class HiddenLinkCheckerApiClient:
    """Call the API without accessing persistence or domain internals."""

    def __init__(self, settings: WebSettings) -> None:
        self._base_url = settings.api_base_url.rstrip("/")

    async def create_link_check(
        self, url: str, include_dom: bool, cookies: Mapping[str, str]
    ) -> CreateLinkCheckResponse:
        """Submit a link check using the browser's API session cookie."""
        async with httpx.AsyncClient(base_url=self._base_url, cookies=cookies) as client:
            response = await client.post(
                "/v1/link-checks", json={"url": url, "include_dom": include_dom}
            )
        response.raise_for_status()
        return CreateLinkCheckResponse.model_validate(response.json())

    async def list_link_checks(self, cookies: Mapping[str, str]) -> list[LinkCheckHistoryItem]:
        """Load history visible to the current user."""
        async with httpx.AsyncClient(base_url=self._base_url, cookies=cookies) as client:
            response = await client.get("/v1/me/link-checks")
        response.raise_for_status()
        return [LinkCheckHistoryItem.model_validate(item) for item in response.json()]

    async def get_link_check(
        self, check_id: UUID, cookies: Mapping[str, str], page: int = 1, page_size: int = 20
    ) -> LinkCheckResponse:
        """Load one link check visible to the current user."""
        async with httpx.AsyncClient(base_url=self._base_url, cookies=cookies) as client:
            response = await client.get(
                f"/v1/link-checks/{check_id}", params={"page": page, "page_size": page_size}
            )
        response.raise_for_status()
        return LinkCheckResponse.model_validate(response.json())

    async def get_current_user(self, cookies: Mapping[str, str]) -> CurrentUserResponse:
        """Return the profile resolved by the API from the session cookie."""
        async with httpx.AsyncClient(base_url=self._base_url, cookies=cookies) as client:
            response = await client.get("/v1/me")
        response.raise_for_status()
        return CurrentUserResponse.model_validate(response.json())

    async def logout(self, cookies: Mapping[str, str]) -> None:
        """Ask the API to revoke the server-side session."""
        async with httpx.AsyncClient(base_url=self._base_url, cookies=cookies) as client:
            response = await client.post("/v1/auth/logout")
        response.raise_for_status()

    def google_login_url(self) -> str:
        """Return the API endpoint that begins the Google OIDC redirect flow."""
        return f"{self._base_url}/v1/auth/google/start"
