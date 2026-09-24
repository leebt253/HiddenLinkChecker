"""Queue boundary separating API request handling from link processing."""

from collections.abc import Callable
from threading import Thread
from typing import Protocol
from uuid import UUID


class LinkCheckQueue(Protocol):
    """A queue that schedules only the original submitted URL for processing."""

    def enqueue(self, check_id: UUID) -> None:
        """Schedule a persisted link check for processing."""


class InMemoryLinkCheckQueue:
    """Development queue that processes jobs in daemon background threads."""

    def __init__(self, processor: Callable[[UUID], None] | None = None) -> None:
        self.enqueued_check_ids: list[UUID] = []
        self._processor = processor

    def enqueue(self, check_id: UUID) -> None:
        self.enqueued_check_ids.append(check_id)
        if self._processor is not None:
            Thread(target=self._processor, args=(check_id,), daemon=True).start()
