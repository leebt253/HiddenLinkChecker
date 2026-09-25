"""Shared URL boundary validation for link checks."""

from urllib.parse import urlsplit, urlunsplit

from shared_contracts.limits import MAX_INPUT_URL_CHARACTERS


class InvalidInputUrlError(ValueError):
    """Raised when a submitted link-check URL is not an absolute HTTP URL."""


def normalize_input_url(submitted_url: str) -> str:
    """Return a normalized absolute HTTP(S) URL or raise InvalidInputUrlError."""
    candidate = submitted_url.strip()
    if len(candidate) > MAX_INPUT_URL_CHARACTERS:
        raise InvalidInputUrlError("The submitted URL exceeds the supported length limit.")
    try:
        parsed_url = urlsplit(candidate)
        hostname = parsed_url.hostname
        _ = parsed_url.port
    except ValueError as error:
        raise InvalidInputUrlError("The submitted URL has an invalid host or port.") from error

    if parsed_url.scheme not in {"http", "https"}:
        raise InvalidInputUrlError("Only http and https URLs are supported.")
    if not parsed_url.netloc or not hostname:
        raise InvalidInputUrlError("A submitted URL must include a host.")
    if parsed_url.username or parsed_url.password:
        raise InvalidInputUrlError("URLs containing credentials are not supported.")

    path = parsed_url.path or "/"
    return urlunsplit(
        (parsed_url.scheme.lower(), parsed_url.netloc.lower(), path, parsed_url.query, "")
    )
