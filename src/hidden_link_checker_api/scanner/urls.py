"""Shared URL boundary validation for link checks."""

from urllib.parse import urlsplit, urlunsplit


class InvalidInputUrlError(ValueError):
    """Raised when a submitted link-check URL is not an absolute HTTP URL."""


def normalize_input_url(submitted_url: str) -> str:
    """Return a normalized absolute HTTP(S) URL or raise InvalidInputUrlError."""
    candidate = submitted_url.strip()
    parsed_url = urlsplit(candidate)

    if parsed_url.scheme not in {"http", "https"}:
        raise InvalidInputUrlError("Only http and https URLs are supported.")
    if not parsed_url.netloc:
        raise InvalidInputUrlError("A submitted URL must include a host.")
    if parsed_url.username or parsed_url.password:
        raise InvalidInputUrlError("URLs containing credentials are not supported.")

    path = parsed_url.path or "/"
    return urlunsplit(
        (parsed_url.scheme.lower(), parsed_url.netloc.lower(), path, parsed_url.query, "")
    )
