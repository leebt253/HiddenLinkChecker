"""Synchronous URL inspection and minimal history use cases."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from hidden_link_checker_api.domain.models import (
    AuthenticatedUser,
    LinkCheck,
    LinkCheckStatus,
    UrlCheckHistory,
)
from hidden_link_checker_api.repositories.link_checks import UrlCheckRepository
from hidden_link_checker_api.scanner.urls import InvalidInputUrlError, normalize_input_url


class LinkCheckProcessor(Protocol):
    """Fetch and inspect one submitted URL without persisting its result."""

    def process(self, link_check: LinkCheck) -> None: ...


class LinkCheckService:
    """Run one scan, return ephemeral findings, and persist URL history only."""

    def __init__(
        self, repository: UrlCheckRepository, processor: LinkCheckProcessor
    ) -> None:
        self._repository = repository
        self._processor = processor

    def check(self, user: AuthenticatedUser, submitted_url: str) -> LinkCheck:
        """Inspect a URL synchronously and store only its submitted URL and timestamp."""
        now = datetime.now(UTC)
        try:
            normalized_url = normalize_input_url(submitted_url)
            link_check = LinkCheck(
                user_id=user.id,
                submitted_url=submitted_url,
                normalized_url=normalized_url,
                created_at=now,
            )
            self._processor.process(link_check)
        except InvalidInputUrlError as error:
            link_check = LinkCheck(
                user_id=user.id,
                submitted_url=submitted_url,
                normalized_url="",
                created_at=now,
                status=LinkCheckStatus.FAILED,
                error_code="invalid_input_url",
                limitations=[str(error)],
                completed_at=now,
            )
        finally:
            self._repository.add(
                UrlCheckHistory(
                    id=link_check.id,
                    user_id=user.id,
                    url=submitted_url,
                    checked_at=now,
                )
            )
        return link_check

    def list_history(self, user: AuthenticatedUser) -> list[UrlCheckHistory]:
        return self._repository.list_owned(user.id)

    def delete_history(self, user: AuthenticatedUser, check_id: UUID) -> bool:
        return self._repository.delete_owned(user.id, check_id)
