"""Ownership-scoped URL history persistence."""

from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from hidden_link_checker_api.domain.models import LinkCheck, LinkCheckStatus


class LinkCheckRepository(Protocol):
    """Persistence boundary for URL history and active in-memory scans."""

    def add(self, link_check: LinkCheck) -> None:
        """Store the checked URL and make the active scan available to the worker."""

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        """Return a URL check only when it belongs to the requesting user."""

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        """Return an active scan for the worker."""

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        """Return URL history for the requesting user."""

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        """Delete one URL history record owned by the requesting user."""


class InMemoryLinkCheckRepository:
    """In-memory adapter used by tests and explicitly configured prototypes."""

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

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        return self._checks.get(check_id)

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        checks = [self._checks[check_id] for check_id in self._checks_by_user[user_id]]
        return sorted(checks, key=lambda check: check.created_at, reverse=True)

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        link_check = self.get_owned(user_id, check_id)
        if link_check is None:
            return False
        del self._checks[check_id]
        self._checks_by_user[user_id].remove(check_id)
        return True


class PostgreSQLLinkCheckRepository:
    """PostgreSQL adapter that persists URL/date only, never scan results."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._active_checks: dict[UUID, LinkCheck] = {}

    def add(self, link_check: LinkCheck) -> None:
        query = """
            INSERT INTO url_checks (id, user_id, url, checked_at)
            VALUES (%s, %s, %s, %s)
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                query,
                (link_check.id, link_check.user_id, link_check.submitted_url, link_check.created_at),
            )
        self._active_checks[link_check.id] = link_check

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        active_check = self._active_checks.get(check_id)
        if active_check is not None and active_check.user_id == user_id:
            return active_check
        return self._get_history("user_id = %s AND id = %s", (user_id, check_id))

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        return self._active_checks.get(check_id)

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        query = """
            SELECT id, user_id, url, checked_at
            FROM url_checks
            WHERE user_id = %s
            ORDER BY checked_at DESC
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (user_id,))
            return [_history_to_link_check(row) for row in cursor.fetchall()]

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM url_checks WHERE user_id = %s AND id = %s", (user_id, check_id))
            deleted = cursor.rowcount == 1
        self._active_checks.pop(check_id, None)
        return deleted

    def save_processed(self, link_check: LinkCheck) -> None:
        """Keep results available during this process without writing them to PostgreSQL."""
        self._active_checks[link_check.id] = link_check

    def _get_history(self, predicate: str, parameters: tuple[object, ...]) -> LinkCheck | None:
        query = f"SELECT id, user_id, url, checked_at FROM url_checks WHERE {predicate}"
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            row = cursor.fetchone()
        return _history_to_link_check(row) if row else None

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, object]]]:
        with psycopg.connect(self._database_url) as connection:
            yield connection


def _history_to_link_check(row: dict[str, object]) -> LinkCheck:
    checked_at = row["checked_at"]
    return LinkCheck(
        id=row["id"],
        user_id=row["user_id"],
        submitted_url=row["url"],
        normalized_url=row["url"],
        include_dom=False,
        status=LinkCheckStatus.COMPLETED,
        created_at=checked_at,
        completed_at=checked_at,
    )
