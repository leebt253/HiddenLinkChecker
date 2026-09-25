"""Ownership-scoped persistence for minimal URL-check history."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from hidden_link_checker_api.domain.models import UrlCheckHistory


class UrlCheckRepository(Protocol):
    """Persistence port for URL and timestamp only."""

    def add(self, item: UrlCheckHistory) -> None:
        """Persist the minimal history record after one request finishes."""

    def list_owned(self, user_id: UUID) -> list[UrlCheckHistory]:
        """List only history owned by the authenticated user."""

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        """Delete one history record only when it belongs to the user."""


class InMemoryUrlCheckRepository:
    """Test and prototype adapter that stores only minimal history fields."""

    def __init__(self) -> None:
        self._items: dict[UUID, UrlCheckHistory] = {}

    def add(self, item: UrlCheckHistory) -> None:
        self._items[item.id] = item

    def list_owned(self, user_id: UUID) -> list[UrlCheckHistory]:
        return sorted(
            (item for item in self._items.values() if item.user_id == user_id),
            key=lambda item: item.checked_at,
            reverse=True,
        )

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        item = self._items.get(check_id)
        if item is None or item.user_id != user_id:
            return False
        del self._items[check_id]
        return True


class PostgreSQLUrlCheckRepository:
    """PostgreSQL adapter that never receives or persists scan results."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def add(self, item: UrlCheckHistory) -> None:
        query = """
            INSERT INTO url_checks (id, user_id, url, checked_at)
            VALUES (%s, %s, %s, %s)
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, (item.id, item.user_id, item.url, item.checked_at))

    def list_owned(self, user_id: UUID) -> list[UrlCheckHistory]:
        query = """
            SELECT id, user_id, url, checked_at
            FROM url_checks
            WHERE user_id = %s
            ORDER BY checked_at DESC
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (user_id,))
            return [_to_history(row) for row in cursor.fetchall()]

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM url_checks WHERE user_id = %s AND id = %s",
                (user_id, check_id),
            )
            return cursor.rowcount == 1

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, object]]]:
        with psycopg.connect(self._database_url) as connection:
            yield connection


def _to_history(row: dict[str, object]) -> UrlCheckHistory:
    return UrlCheckHistory(
        id=row["id"], user_id=row["user_id"], url=row["url"], checked_at=row["checked_at"]
    )


# Backwards-compatible names retained for callers that refer to history explicitly.
UrlCheckHistoryRepository = UrlCheckRepository
InMemoryUrlCheckHistoryRepository = InMemoryUrlCheckRepository
PostgreSQLUrlCheckHistoryRepository = PostgreSQLUrlCheckRepository
