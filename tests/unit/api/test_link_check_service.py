from uuid import uuid4

from hidden_link_checker_api.domain.models import (
    AuthenticatedUser,
    ElementType,
    LinkCheckStatus,
    LinkResult,
    UrlCheckHistory,
    Visibility,
)
from hidden_link_checker_api.repositories.link_checks import InMemoryUrlCheckRepository
from hidden_link_checker_api.services.link_checks import LinkCheckService


class SuccessfulProcessor:
    def process(self, link_check) -> None:
        link_check.status = LinkCheckStatus.COMPLETED
        link_check.final_url = link_check.normalized_url
        link_check.http_status = 200
        link_check.links = [
            LinkResult(
                element_type=ElementType.TEXT,
                object_reference="link",
                source_url="/offer",
                actual_url="https://example.test/offer",
                visibility=Visibility.DIRECT,
                visible_text="Offer",
            )
        ]


def test_check_returns_findings_and_persists_only_minimal_history() -> None:
    repository = InMemoryUrlCheckRepository()
    service = LinkCheckService(repository, SuccessfulProcessor())
    user = AuthenticatedUser(id=uuid4())

    result = service.check(user, "https://example.test")

    assert result.status is LinkCheckStatus.COMPLETED
    assert result.links[0].actual_url == "https://example.test/offer"
    history = repository.list_owned(user.id)
    assert history == [
        UrlCheckHistory(
            id=result.id,
            user_id=user.id,
            url="https://example.test",
            checked_at=result.created_at,
        )
    ]
    assert not hasattr(history[0], "links")
    assert not hasattr(history[0], "status")


def test_invalid_input_returns_failed_result_and_minimal_history() -> None:
    repository = InMemoryUrlCheckRepository()
    service = LinkCheckService(repository, SuccessfulProcessor())
    user = AuthenticatedUser(id=uuid4())

    result = service.check(user, "file:///etc/passwd")

    assert result.status is LinkCheckStatus.FAILED
    assert result.error_code == "invalid_input_url"
    assert result.links == []
    assert repository.list_owned(user.id)[0].url == "file:///etc/passwd"


def test_history_access_and_delete_are_scoped_to_owner() -> None:
    repository = InMemoryUrlCheckRepository()
    service = LinkCheckService(repository, SuccessfulProcessor())
    owner = AuthenticatedUser(id=uuid4())
    another_user = AuthenticatedUser(id=uuid4())
    result = service.check(owner, "https://example.test")

    assert service.list_history(another_user) == []
    assert not service.delete_history(another_user, result.id)
    assert service.delete_history(owner, result.id)
