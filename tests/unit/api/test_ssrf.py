from ipaddress import ip_address

import pytest

from hidden_link_checker_api.scanner import ssrf
from hidden_link_checker_api.scanner.ssrf import (
    UnsafeNavigationUrlError,
    ensure_safe_navigation_url,
)


def test_safe_navigation_url_rejects_private_resolved_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda _: {ip_address("127.0.0.1")})

    with pytest.raises(UnsafeNavigationUrlError):
        ensure_safe_navigation_url("https://example.test")


def test_safe_navigation_url_allows_public_resolved_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda _: {ip_address("93.184.216.34")})

    assert ensure_safe_navigation_url("https://example.test") == "https://example.test/"