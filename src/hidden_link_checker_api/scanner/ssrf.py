"""SSRF policy checks for the submitted navigation URL and its redirects."""

import ipaddress
import socket
from urllib.parse import urlsplit

from hidden_link_checker_api.scanner.urls import InvalidInputUrlError, normalize_input_url

METADATA_HOSTS = {"metadata.google.internal", "metadata"}


class UnsafeNavigationUrlError(ValueError):
    """Raised when a navigation target resolves to a prohibited address."""


def ensure_safe_navigation_url(candidate_url: str) -> str:
    """Validate an input or redirect URL before a worker connects to it."""
    normalized_url = normalize_input_url(candidate_url)
    hostname = urlsplit(normalized_url).hostname
    if hostname is None:
        raise InvalidInputUrlError("A submitted URL must include a host.")
    if hostname.lower() in METADATA_HOSTS or hostname.lower().endswith(".metadata.google.internal"):
        raise UnsafeNavigationUrlError("Cloud metadata endpoints are not allowed.")

    addresses = _resolve_addresses(hostname)
    if any(_is_prohibited_address(address) for address in addresses):
        raise UnsafeNavigationUrlError("The URL resolves to a prohibited network address.")
    return normalized_url


def _resolve_addresses(hostname: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        address_info = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise UnsafeNavigationUrlError("The URL host could not be resolved.") from error

    addresses = {ipaddress.ip_address(item[4][0]) for item in address_info}
    if not addresses:
        raise UnsafeNavigationUrlError("The URL host could not be resolved.")
    return addresses


def _is_prohibited_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_unspecified,
            address.is_reserved,
        )
    )