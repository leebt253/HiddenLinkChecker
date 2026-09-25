"""Public request and response models shared by API and web modules."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

LinkCheckStatus = Literal["completed", "partial", "failed"]
ElementType = Literal["text", "image", "background"]
Visibility = Literal["direct", "indirect"]


class CreateLinkCheckRequest(BaseModel):
    """Payload for synchronously inspecting one page."""

    url: str = Field(min_length=1, max_length=8192)


class LinkResultResponse(BaseModel):
    """A finding that exists only in this response."""

    element_type: ElementType
    object_reference: str | None
    source_url: str
    actual_url: str
    visibility: Visibility
    visible_text: str | None = None
    alt_text: str | None = None
    position: dict[str, float] | None = None


class LinkCheckResponse(BaseModel):
    """The complete ephemeral result of one synchronous URL check."""

    check_id: UUID
    status: LinkCheckStatus
    submitted_url: str
    normalized_url: str | None
    final_url: str | None
    http_status: int | None = None
    error_code: str | None = None
    dom_excerpt: str | None = None
    limitations: list[str] = Field(default_factory=list)
    checked_at: datetime
    links: list[LinkResultResponse] = Field(default_factory=list)


class LinkCheckHistoryItem(BaseModel):
    """Minimal persisted history; intentionally excludes scan status and results."""

    check_id: UUID
    url: str
    checked_at: datetime


class CurrentUserResponse(BaseModel):
    """Public profile for the user resolved from the current server-side session."""

    id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None
