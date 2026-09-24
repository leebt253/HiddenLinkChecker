from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from hidden_link_checker_api.config import ApiSettings
from hidden_link_checker_api.domain.models import User
from hidden_link_checker_api.main import create_app


class FakeAuthenticationService:
    """API controller double that resolves a user only from a session token."""

    def __init__(self) -> None:
        self.user = User(
            id=uuid4(), google_subject="subject-123", email="person@example.test",
            display_name="Nguyen Van A", avatar_url=None,
            created_at=datetime.now(UTC), last_login_at=datetime.now(UTC),
        )
        self.revoked_tokens: list[str] = []

    def begin_google_login(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    def get_user_from_session(self, session_token: str | None) -> User | None:
        return self.user if session_token == "valid-session" else None

    def logout(self, session_token: str | None) -> None:
        if session_token:
            self.revoked_tokens.append(session_token)


def _client() -> tuple[TestClient, FakeAuthenticationService]:
    settings = ApiSettings(session_cookie_name="session")
    app = create_app(settings)
    service = FakeAuthenticationService()
    app.state.authentication_service = service
    return TestClient(app), service


def test_me_rejects_missing_session_cookie() -> None:
    client, _ = _client()

    response = client.get("/v1/me")

    assert response.status_code == 401


def test_me_returns_the_profile_resolved_from_session_cookie() -> None:
    client, _ = _client()

    response = client.get("/v1/me", cookies={"session": "valid-session"})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Nguyen Van A"
    assert "google_subject" not in response.json()


def test_logout_revokes_session_and_clears_cookie() -> None:
    client, service = _client()

    response = client.post("/v1/auth/logout", cookies={"session": "valid-session"})

    assert response.status_code == 204
    assert service.revoked_tokens == ["valid-session"]
    assert "session=" in response.headers["set-cookie"]