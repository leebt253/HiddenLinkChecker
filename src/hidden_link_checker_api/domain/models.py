"""Domain entities owned by the API module."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4


class LinkCheckStatus(StrEnum):
    """States in the asynchronous link-check lifecycle."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ElementType(StrEnum):
    """DOM source types supported by the MVP extractor."""

    TEXT = "text"
    IMAGE = "image"
    BACKGROUND = "background"


class Visibility(StrEnum):
    """Whether a link is directly visible as text or tied to another object."""

    DIRECT = "direct"
    INDIRECT = "indirect"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The identity resolved by the API authentication boundary."""

    id: UUID


@dataclass(frozen=True, slots=True)
class User:
    """A local account mapped to a stable Google OpenID Connect subject."""

    id: UUID
    google_subject: str
    email: str
    display_name: str | None
    avatar_url: str | None
    created_at: datetime
    last_login_at: datetime


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    """Verified identity claims required to create or update a local user."""

    subject: str
    email: str
    display_name: str | None
    avatar_url: str | None


@dataclass(frozen=True, slots=True)
class UserSession:
    """A revocable server-side session represented by a hashed opaque token."""

    token_hash: bytes
    user_id: UUID
    expires_at: datetime

    @classmethod
    def from_token(cls, token: str, user_id: UUID, expires_at: datetime) -> "UserSession":
        """Build a persistable session without retaining its plaintext token."""
        return cls(token_hash=_hash_secret(token), user_id=user_id, expires_at=expires_at)

    @classmethod
    def lifetime(cls, days: int) -> timedelta:
        """Return the configured server-side session lifetime."""
        return timedelta(days=days)


@dataclass(frozen=True, slots=True)
class OAuthLoginTransaction:
    """One-time state and nonce values stored server-side for an OIDC login."""

    state_hash: bytes
    nonce_hash: bytes
    expires_at: datetime

    @classmethod
    def from_values(cls, state: str, nonce: str, expires_at: datetime) -> "OAuthLoginTransaction":
        """Build a persistable one-time login transaction without plaintext secrets."""
        return cls(
            state_hash=_hash_secret(state),
            nonce_hash=_hash_secret(nonce),
            expires_at=expires_at,
        )

    @staticmethod
    def hash_value(value: str) -> bytes:
        """Hash callback state or a verified nonce for persisted-state comparison."""
        return _hash_secret(value)


def _hash_secret(value: str) -> bytes:
    from hashlib import sha256

    return sha256(value.encode("utf-8")).digest()


@dataclass(frozen=True, slots=True)
class LinkResult:
    """A parsed URL retained as data without being requested by the system."""

    link_check_id: UUID
    element_type: ElementType
    object_reference: str | None
    source_url: str
    actual_url: str
    visibility: Visibility
    visible_text: str | None = None
    alt_text: str | None = None
    position: dict[str, float] | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class LinkCheck:
    """An asynchronously processed URL owned by one authenticated user."""

    user_id: UUID
    submitted_url: str
    normalized_url: str
    include_dom: bool
    id: UUID = field(default_factory=uuid4)
    status: LinkCheckStatus = LinkCheckStatus.QUEUED
    final_url: str | None = None
    http_status: int | None = None
    error_code: str | None = None
    dom_reference: str | None = None
    limitations: list[str] = field(default_factory=list)
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    links: list[LinkResult] = field(default_factory=list)
