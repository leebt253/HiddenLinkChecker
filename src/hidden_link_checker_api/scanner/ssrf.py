"""SSRF policy checks for the submitted navigation URL and its redirects."""

import ipaddress
import socket
from typing import Self
from urllib.parse import urlsplit

from hidden_link_checker_api.scanner.urls import InvalidInputUrlError, normalize_input_url

METADATA_HOSTS = {"metadata.google.internal", "metadata"}


class UnsafeNavigationUrlError(ValueError):
    """Raised when a navigation target resolves to a prohibited address."""


class NavigationDnsError(ValueError):
    """Raised when the input host cannot be resolved to a usable address."""


class SafeNavigationURL(str):
    """Normalized URL carrying the exact safe DNS answers to pin at connect time."""

    def __new__(
        cls,
        normalized_url: str,
        hostname: str,
        addresses: frozenset[ipaddress.IPv4Address | ipaddress.IPv6Address],
    ) -> Self:
        instance = super().__new__(cls, normalized_url)
        instance.hostname = hostname
        instance.addresses = addresses
        return instance


def ensure_safe_navigation_url(candidate_url: str) -> SafeNavigationURL:
    """Validate a URL and retain its verified addresses for a pinned connection."""
    normalized_url = normalize_input_url(candidate_url)
    hostname = urlsplit(normalized_url).hostname
    if hostname is None:
        raise InvalidInputUrlError("A submitted URL must include a host.")
    if hostname.lower() in METADATA_HOSTS or hostname.lower().endswith(".metadata.google.internal"):
        raise UnsafeNavigationUrlError("Cloud metadata endpoints are not allowed.")

    try:
        addresses = frozenset({ipaddress.ip_address(hostname)})
    except ValueError:
        addresses = frozenset(_resolve_addresses(hostname))
    if any(_is_prohibited_address(address) for address in addresses):
        raise UnsafeNavigationUrlError("The URL resolves to a prohibited network address.")
    return SafeNavigationURL(normalized_url, hostname, addresses)


def _resolve_addresses(hostname: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        address_info = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as error:
        raise NavigationDnsError("The URL host could not be resolved.") from error

    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in address_info}
    except (IndexError, ValueError) as error:
        raise NavigationDnsError("The URL host returned invalid DNS addresses.") from error
    if not addresses:
        raise NavigationDnsError("The URL host could not be resolved.")
    return addresses


def _is_prohibited_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    mapped_address = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
    if mapped_address is not None and _is_prohibited_address(mapped_address):
        return True
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_unspecified,
            address.is_reserved,
            not address.is_global,
        )
    )
