from ipaddress import ip_address

import httpcore
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


def test_safe_navigation_url_rejects_host_with_mixed_public_and_private_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ssrf,
        "_resolve_addresses",
        lambda _: {ip_address("93.184.216.34"), ip_address("10.0.0.8")},
    )

    with pytest.raises(UnsafeNavigationUrlError):
        ensure_safe_navigation_url("https://rebind.example")


def test_safe_navigation_url_rejects_metadata_names_without_dns_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ssrf,
        "_resolve_addresses",
        lambda _: pytest.fail("metadata names must be rejected before DNS lookup"),
    )

    with pytest.raises(UnsafeNavigationUrlError):
        ensure_safe_navigation_url("http://metadata.google.internal/latest/meta-data/")


def test_safe_navigation_url_allows_public_resolved_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda _: {ip_address("93.184.216.34")})

    safe_url = ensure_safe_navigation_url("https://example.test")

    assert safe_url == "https://example.test/"
    assert safe_url.addresses == frozenset({ip_address("93.184.216.34")})


def test_pinned_backend_connects_to_the_verified_ip_without_resolving_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hidden_link_checker_api.scanner.pinned_transport import _PinnedNetworkBackend

    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda _: {ip_address("93.184.216.34")})
    safe_url = ensure_safe_navigation_url("https://example.test")
    connected_hosts: list[str] = []

    class RecordingBackend(httpcore.NetworkBackend):
        def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
            connected_hosts.append(host)
            return httpcore.MockBackend([]).connect_tcp(host, port, timeout)

        def connect_unix_socket(self, path, timeout=None, socket_options=None):
            raise AssertionError("The pinned URL transport must not use Unix sockets.")

    backend = _PinnedNetworkBackend(safe_url.hostname, safe_url.addresses)
    backend._backend = RecordingBackend()

    backend.connect_tcp("example.test", 443)

    assert connected_hosts == ["93.184.216.34"]
