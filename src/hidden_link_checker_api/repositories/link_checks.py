"""Ownership-scoped persistence port for link checks."""

from collections import defaultdict
from typing import Protocol
from uuid import UUID

from hidden_link_checker_api.domain.models import LinkCheck


class LinkCheckRepository(Protocol):
    """Persistence contract that never exposes an unowned link check."""

    def add(self, link_check: LinkCheck) -> None:
        """Persist a queued link check."""

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        """Return a link check only when it belongs to the requesting user."""

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        """Return the requesting user's checks in reverse creation order."""

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        """Delete a link check only when it belongs to the requesting user."""


class InMemoryLinkCheckRepository:
    """Development and unit-test adapter; production must use PostgreSQL."""

    def __init__(self) -> None:
        self._checks: dict[UUID, LinkCheck] = {}
        self._checks_by_user: dict[UUID, set[UUID]] = defaultdict(set)

    def add(self, link_check: LinkCheck) -> None:
        self._checks[link_check.id] = link_check
        self._checks_by_user[link_check.user_id].add(link_check.id)

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        if check_id not in self._checks_by_user[user_id]:
            return None
        return self._checks[check_id]

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        checks = [self._checks[check_id] for check_id in self._checks_by_user[user_id]]
        return sorted(checks, key=lambda link_check: link_check.created_at, reverse=True)

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        link_check = self.get_owned(user_id, check_id)
        if link_check is None:
            return False
        del self._checks[check_id]
        self._checks_by_user[user_id].remove(check_id)
        return True
