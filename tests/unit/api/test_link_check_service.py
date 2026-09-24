from uuid import uuid4

from hidden_link_checker_api.domain.models import AuthenticatedUser, LinkCheckStatus
from hidden_link_checker_api.repositories.link_checks import InMemoryLinkCheckRepository
from hidden_link_checker_api.services.link_checks import LinkCheckService
from hidden_link_checker_api.workers.queue import InMemoryLinkCheckQueue


def test_create_persists_owned_check_before_queuing() -> None:
    repository = InMemoryLinkCheckRepository()
    queue = InMemoryLinkCheckQueue()
    service = LinkCheckService(repository, queue)
    user = AuthenticatedUser(id=uuid4())

    link_check = service.create(user, "https://example.test", include_dom=True)

    assert link_check.status is LinkCheckStatus.QUEUED
    assert repository.get_owned(user.id, link_check.id) is link_check
    assert queue.enqueued_check_ids == [link_check.id]


def test_get_does_not_expose_another_users_link_check() -> None:
    repository = InMemoryLinkCheckRepository()
    service = LinkCheckService(repository, InMemoryLinkCheckQueue())
    owner = AuthenticatedUser(id=uuid4())
    other_user = AuthenticatedUser(id=uuid4())
    link_check = service.create(owner, "https://example.test", include_dom=True)

    assert service.get(other_user, link_check.id) is None