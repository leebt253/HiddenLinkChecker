"""Ownership-scoped persistence port for link checks."""

from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from hidden_link_checker_api.domain.models import (
    ElementType,
    LinkCheck,
    LinkCheckStatus,
    LinkResult,
    Visibility,
)


class LinkCheckRepository(Protocol):
    """Persistence contract that never exposes an unowned link check."""

    def add(self, link_check: LinkCheck) -> None:
        """Persist a queued link check."""

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        """Return a link check only when it belongs to the requesting user."""

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        """Return a link check for the internal worker by identifier."""

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        """Return the requesting user's checks in reverse creation order."""

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        """Delete a link check only when it belongs to the requesting user."""

    def update_notes(self, user_id: UUID, check_id: UUID, notes: str | None) -> LinkCheck | None:
        """Update owner-editable metadata and return the owned check."""


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

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        return self._checks.get(check_id)

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

    def update_notes(self, user_id: UUID, check_id: UUID, notes: str | None) -> LinkCheck | None:
        link_check = self.get_owned(user_id, check_id)
        if link_check is None:
            return None
        link_check.notes = notes
        return link_check


class PostgreSQLLinkCheckRepository:
    """PostgreSQL adapter with ownership predicates on every user operation."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def add(self, link_check: LinkCheck) -> None:
        query = """
            INSERT INTO link_checks
                (id, user_id, submitted_url, normalized_url, include_dom, status, limitations)
            VALUES (%(id)s, %(user_id)s, %(submitted_url)s, %(normalized_url)s,
                    %(include_dom)s, %(status)s, %(limitations)s::jsonb)
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, _check_params(link_check))

    def get_owned(self, user_id: UUID, check_id: UUID) -> LinkCheck | None:
        return self._get("user_id = %s AND id = %s", (user_id, check_id))

    def get_by_id(self, check_id: UUID) -> LinkCheck | None:
        return self._get("id = %s", (check_id,))

    def list_owned(self, user_id: UUID) -> list[LinkCheck]:
        query = "SELECT * FROM link_checks WHERE user_id = %s ORDER BY created_at DESC"
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (user_id,))
            return [_to_link_check(row, self._load_results(row["id"])) for row in cursor.fetchall()]

    def delete_owned(self, user_id: UUID, check_id: UUID) -> bool:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM link_checks WHERE user_id = %s AND id = %s", (user_id, check_id))
            return cursor.rowcount == 1

    def update_notes(self, user_id: UUID, check_id: UUID, notes: str | None) -> LinkCheck | None:
        query = """
            UPDATE link_checks SET notes = %s
            WHERE user_id = %s AND id = %s
            RETURNING *
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (notes, user_id, check_id))
            row = cursor.fetchone()
        return _to_link_check(row, self._load_results(row["id"])) if row else None

    def _load_results(self, check_id: UUID) -> list[LinkResult]:
        query = "SELECT * FROM link_results WHERE link_check_id = %s ORDER BY created_at"
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (check_id,))
            return [_to_link_result(row) for row in cursor.fetchall()]

    def save_processed(self, link_check: LinkCheck) -> None:
        query = """
            UPDATE link_checks
            SET status = %s, final_url = %s, http_status = %s, error_code = %s,
                dom_reference = %s, limitations = %s::jsonb, completed_at = %s,
                started_at = COALESCE(started_at, created_at)
            WHERE id = %s
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, (
                link_check.status.value, link_check.final_url, link_check.http_status,
                link_check.error_code, link_check.dom_reference, _json(link_check.limitations),
                link_check.completed_at, link_check.id,
            ))
            cursor.execute("DELETE FROM link_results WHERE link_check_id = %s", (link_check.id,))
            for result in link_check.links:
                cursor.execute(
                    """INSERT INTO link_results
                    (id, link_check_id, element_type, object_reference, source_url, actual_url,
                     visibility, visible_text, alt_text, position)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
                    (result.id, result.link_check_id, result.element_type.value,
                     result.object_reference, result.source_url, result.actual_url,
                     result.visibility.value, result.visible_text, result.alt_text,
                     _json(result.position)),
                )

    def _get(self, predicate: str, parameters: tuple[object, ...]) -> LinkCheck | None:
        query = f"SELECT * FROM link_checks WHERE {predicate}"
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            row = cursor.fetchone()
        return _to_link_check(row, self._load_results(row["id"])) if row else None

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, object]]]:
        with psycopg.connect(self._database_url) as connection:
            yield connection


def _check_params(link_check: LinkCheck) -> dict[str, object]:
    return {
        "id": link_check.id, "user_id": link_check.user_id,
        "submitted_url": link_check.submitted_url, "normalized_url": link_check.normalized_url,
        "include_dom": link_check.include_dom, "status": link_check.status.value,
        "limitations": _json(link_check.limitations),
    }


def _to_link_check(row: dict[str, object], links: list[LinkResult]) -> LinkCheck:
    return LinkCheck(
        id=row["id"], user_id=row["user_id"], submitted_url=row["submitted_url"],
        normalized_url=row["normalized_url"], include_dom=row.get("include_dom", True),
        status=LinkCheckStatus(row["status"]), final_url=row["final_url"], http_status=row.get("http_status"),
        error_code=row.get("error_code"), dom_reference=row["dom_reference"],
        limitations=list(row.get("limitations") or []), notes=row.get("notes"),
        created_at=row["created_at"], completed_at=row["completed_at"],
        links=links,
    )


def _to_link_result(row: dict[str, object]) -> LinkResult:
    return LinkResult(
        id=row["id"], link_check_id=row["link_check_id"],
        element_type=ElementType(row["element_type"]), object_reference=row["object_reference"],
        source_url=row["source_url"], actual_url=row["actual_url"],
        visibility=Visibility(row["visibility"]), visible_text=row["visible_text"],
        alt_text=row["alt_text"], position=row["position"],
    )


def _json(value: object) -> str:
    import json

    return json.dumps(value)
