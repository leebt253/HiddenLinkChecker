"""Domain entities owned by the API module."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class LinkCheckStatus(StrEnum):
    """Final states returned by one synchronous URL check."""

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
    """A parsed URL returned only in the response for the current request."""

    element_type: ElementType
    object_reference: str | None
    source_url: str
    actual_url: str
    visibility: Visibility
    visible_text: str | None = None
    alt_text: str | None = None
    position: dict[str, float] | None = None


@dataclass(slots=True)
class LinkCheck:
    """Ephemeral scan state; never persist this object or its links."""

    user_id: UUID
    submitted_url: str
    normalized_url: str
    id: UUID = field(default_factory=uuid4)
    status: LinkCheckStatus = LinkCheckStatus.COMPLETED
    final_url: str | None = None
    http_status: int | None = None
    error_code: str | None = None
    dom_excerpt: str | None = None
    limitations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    links: list[LinkResult] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UrlCheckHistory:
    """The only long-lived record created by a link-check request."""

    id: UUID
    user_id: UUID
    url: str
    checked_at: datetime
