"""Use cases for creating and accessing a user's link checks."""

from uuid import UUID

from hidden_link_checker_api.domain.models import AuthenticatedUser, LinkCheck
from hidden_link_checker_api.repositories.link_checks import LinkCheckRepository
from hidden_link_checker_api.scanner.urls import normalize_input_url
from hidden_link_checker_api.workers.queue import LinkCheckQueue


class LinkCheckService:
    """Coordinate validation, persistence and worker scheduling for link checks."""

    def __init__(self, repository: LinkCheckRepository, queue: LinkCheckQueue) -> None:
        self._repository = repository
        self._queue = queue

    def create(self, user: AuthenticatedUser, submitted_url: str, include_dom: bool) -> LinkCheck:
        """Create a user-owned check and enqueue it after it is persisted."""
        link_check = LinkCheck(
            user_id=user.id,
            submitted_url=submitted_url,
            normalized_url=normalize_input_url(submitted_url),
            include_dom=include_dom,
        )
        self._repository.add(link_check)
        self._queue.enqueue(link_check.id)
        return link_check

    def get(self, user: AuthenticatedUser, check_id: UUID) -> LinkCheck | None:
        """Return a check only if it belongs to the authenticated user."""
        return self._repository.get_owned(user.id, check_id)

    def list(self, user: AuthenticatedUser) -> list[LinkCheck]:
        """Return checks owned by the authenticated user."""
        return self._repository.list_owned(user.id)

    def delete(self, user: AuthenticatedUser, check_id: UUID) -> bool:
        """Delete a check only if it belongs to the authenticated user."""
        return self._repository.delete_owned(user.id, check_id)

    def update_notes(self, user: AuthenticatedUser, check_id: UUID, notes: str | None) -> LinkCheck | None:
        """Update only owner-editable metadata for a link check."""
        return self._repository.update_notes(user.id, check_id, notes)
