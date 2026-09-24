"""Public request and response models for the version one API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

LinkCheckStatus = Literal["queued", "running", "completed", "partial", "failed"]
ElementType = Literal["text", "image", "background"]
Visibility = Literal["direct", "indirect"]


class CreateLinkCheckRequest(BaseModel):
    """Payload for submitting a URL for asynchronous processing."""

    url: str = Field(min_length=1, max_length=8192)
    include_dom: bool = True


class CreateLinkCheckResponse(BaseModel):
    """Response returned after a link check has been queued."""

    check_id: UUID
    status: LinkCheckStatus
    created_at: datetime


class LinkResultResponse(BaseModel):
    """A hidden link extracted from a completed DOM."""

    id: UUID
    element_type: ElementType
    object_reference: str | None
    source_url: str
    actual_url: str
    visibility: Visibility
    visible_text: str | None
    alt_text: str | None
    position: dict[str, float] | None


class LinkCheckResponse(BaseModel):
    """The authenticated user's view of a link check and its findings."""

    check_id: UUID
    status: LinkCheckStatus
    submitted_url: str
    normalized_url: str | None
    final_url: str | None
    http_status: int | None
    error_code: str | None
    dom_reference: str | None
    limitations: list[str]
    created_at: datetime
    completed_at: datetime | None
    links: list[LinkResultResponse]
    total_links: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class LinkCheckHistoryItem(BaseModel):
    """A concise link-check record for the authenticated user's history."""

    check_id: UUID
    status: LinkCheckStatus
    submitted_url: str
    created_at: datetime
    completed_at: datetime | None


class CurrentUserResponse(BaseModel):
    """Public profile for the user resolved from the current server-side session."""

    id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None
