from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from hidden_link_checker_api.domain.models import GoogleIdentity
from hidden_link_checker_api.repositories.auth import InMemoryAuthRepository
from hidden_link_checker_api.services.auth import AuthenticationService, InvalidOAuthCallbackError


class FakeGoogleOAuthClient:
    """Deterministic Google protocol adapter for authentication service tests."""

    def authorization_url(self, state: str, nonce: str) -> str:
        return f"https://accounts.example.test/auth?state={state}&nonce={nonce}"

    async def exchange_code(self, code: str) -> str:
        assert code == "valid-code"
        return "verified-id-token"


class FakeIdTokenVerifier:
    """Returns a verified identity after the Google-specific verifier boundary."""

    def verify(self, raw_id_token: str, expected_nonce_hash: bytes) -> GoogleIdentity:
        assert raw_id_token == "verified-id-token"
        assert expected_nonce_hash
        return GoogleIdentity(
            subject="google-subject-123",
            email="person@example.test",
            display_name="Nguyen Van A",
            avatar_url=None,
        )


def _new_service(repository: InMemoryAuthRepository) -> AuthenticationService:
    return AuthenticationService(
        repository=repository,
        oauth_client=FakeGoogleOAuthClient(),  # type: ignore[arg-type]
        verifier=FakeIdTokenVerifier(),
        session_lifetime=timedelta(days=1),
        transaction_lifetime=timedelta(minutes=5),
    )


@pytest.mark.asyncio
async def test_complete_google_login_creates_user_session_and_updates_existing_user() -> None:
    repository = InMemoryAuthRepository()
    service = _new_service(repository)
    login_url = service.begin_google_login()
    state = parse_qs(urlsplit(login_url).query)["state"][0]

    first_user, first_token = await service.complete_google_login("valid-code", state)

    assert service.get_user_from_session(first_token) == first_user

    second_login_url = service.begin_google_login()
    second_state = parse_qs(urlsplit(second_login_url).query)["state"][0]
    second_user, _ = await service.complete_google_login("valid-code", second_state)

    assert second_user.id == first_user.id


@pytest.mark.asyncio
async def test_complete_google_login_rejects_invalid_or_replayed_state() -> None:
    service = _new_service(InMemoryAuthRepository())

    with pytest.raises(InvalidOAuthCallbackError):
        await service.complete_google_login("valid-code", "unknown-state")


@pytest.mark.asyncio
async def test_logout_revokes_session() -> None:
    repository = InMemoryAuthRepository()
    service = _new_service(repository)
    login_url = service.begin_google_login()
    state = parse_qs(urlsplit(login_url).query)["state"][0]
    _, session_token = await service.complete_google_login("valid-code", state)

    service.logout(session_token)

    assert service.get_user_from_session(session_token) is None