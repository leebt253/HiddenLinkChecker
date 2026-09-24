"""Queue boundary separating API request handling from browser processing."""

from typing import Protocol
from uuid import UUID


class LinkCheckQueue(Protocol):
    """A queue that schedules only the original submitted URL for processing."""

    def enqueue(self, check_id: UUID) -> None:
        """Schedule a persisted link check for processing."""


class InMemoryLinkCheckQueue:
    """Development adapter that records jobs without navigating to any URL."""

    def __init__(self) -> None:
        self.enqueued_check_ids: list[UUID] = []

    def enqueue(self, check_id: UUID) -> None:
        self.enqueued_check_ids.append(check_id)
