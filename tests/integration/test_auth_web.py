from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from hidden_link_checker_web.config import WebSettings
from hidden_link_checker_web.main import create_app
from shared_contracts.api_models import CurrentUserResponse, LinkCheckHistoryItem


class FakeApiClient:
    """Web controller double that represents only public API contract calls."""

    def __init__(self) -> None:
        self.authenticated = False
        self.logout_called = False

    async def get_current_user(self, cookies: object) -> CurrentUserResponse:
        if not self.authenticated:
            request = httpx.Request("GET", "http://api.test/v1/me")
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError("unauthenticated", request=request, response=response)
        return CurrentUserResponse(
            id=uuid4(), email="person@example.test", display_name="Nguyen Van A", avatar_url=None
        )

    async def logout(self, cookies: object) -> None:
        self.logout_called = True
        self.authenticated = False

    async def list_link_checks(self, cookies: object) -> list[LinkCheckHistoryItem]:
        return []

    def google_login_url(self) -> str:
        return "http://api.test/v1/auth/google/start"


def _client() -> tuple[TestClient, FakeApiClient]:
    app = create_app(WebSettings(session_cookie_name="session"))
    api_client = FakeApiClient()
    app.state.api_client = api_client
    return TestClient(app), api_client


def test_login_page_has_google_sign_in_action() -> None:
    client, _ = _client()

    response = client.get("/login")

    assert response.status_code == 200
    assert "Đăng nhập với Google" in response.text
    assert "v1/auth/google/start" in response.text


def test_welcome_redirects_unauthenticated_user_to_login() -> None:
    client, _ = _client()

    response = client.get("/welcome", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_welcome_redirects_authenticated_user_to_dashboard_and_logout_revokes_session() -> None:
    client, api_client = _client()
    api_client.authenticated = True

    welcome_response = client.get("/welcome", follow_redirects=False)
    logout_response = client.post("/logout", follow_redirects=False)

    assert welcome_response.status_code == 303
    assert welcome_response.headers["location"] == "/"
    assert logout_response.status_code == 303
    assert api_client.logout_called
    assert "session=" in logout_response.headers["set-cookie"]


def test_unknown_web_route_uses_custom_error_page() -> None:
    client, _ = _client()

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert "Page not found" in response.text
    assert "Return to dashboard" in response.text