import socket
import ssl
from uuid import uuid4

import httpx
import pytest

from hidden_link_checker_api.domain.models import LinkCheck, LinkCheckStatus
from hidden_link_checker_api.workers.link_check_worker import LinkCheckWorker


def test_worker_fetches_only_input_and_extracts_without_requesting_findings(monkeypatch):
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                '<a href="https://hidden.example/one">About</a>'
                '<script>document.body.insertAdjacentHTML("beforeend", '
                '"<img src=\\\'https://hidden.example/two.png\\\' '
                'srcset=\\\'/hero@2x.png 2x\\\' alt=\\\'Hero\\\'>'
                '<div id=\\\'dynamic\\\' style=\\\'background-image: '
                'url(\\\"https://hidden.example/three.png\\\")\\\'></div>")</script>'
            ),
            request=request,
        )

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(transport=httpx.MockTransport(handler))
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/home",
        normalized_url="https://example.test/home",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.PARTIAL
    assert [result.actual_url for result in link_check.links] == [
        "https://hidden.example/one",
        "https://hidden.example/two.png",
        "https://example.test/hero@2x.png",
        "https://hidden.example/three.png",
    ]
    assert requested_urls == ["https://example.test/home"]
    assert link_check.dom_excerpt is not None
    assert 'id="dynamic"' in link_check.dom_excerpt
    assert any("External page requests were blocked" in item for item in link_check.limitations)


def test_worker_returns_controlled_failed_result_on_fetch_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(transport=httpx.MockTransport(handler))
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test",
        normalized_url="https://example.test/",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "http_503"
    assert link_check.links == []
    assert link_check.limitations


def test_worker_rejects_redirect_to_private_ip_before_requesting_it(monkeypatch):
    from ipaddress import ip_address

    from hidden_link_checker_api.scanner import ssrf

    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            302,
            headers={"location": "http://127.0.0.1/private"},
            request=request,
        )

    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda _: {ip_address("93.184.216.34")})
    worker = LinkCheckWorker(transport=httpx.MockTransport(handler))
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/start",
        normalized_url="https://example.test/start",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "unsafe_navigation_url"
    assert requested_urls == ["https://example.test/start"]


def test_worker_returns_controlled_timeout_result(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(transport=httpx.MockTransport(handler))
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/slow",
        normalized_url="https://example.test/slow",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "timeout"
    assert link_check.links == []


def test_worker_rejects_response_larger_than_configured_limit(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="123456789", request=request)

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(
        transport=httpx.MockTransport(handler), max_response_bytes=8
    )
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/large",
        normalized_url="https://example.test/large",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "resource_limit_exceeded"
    assert any("size limit" in item for item in link_check.limitations)
    assert link_check.links == []


def test_worker_returns_controlled_network_error_without_forwarding_credentials(monkeypatch):
    sent_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_headers.append(request.headers)
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(transport=httpx.MockTransport(handler))
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/offline",
        normalized_url="https://example.test/offline",
    )

    worker.process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "fetch_failed"
    assert sent_headers
    assert "cookie" not in sent_headers[0]
    assert "authorization" not in sent_headers[0]


@pytest.mark.parametrize(
    ("status_code", "error_code", "limitation"),
    [
        (403, "http_403", "denied access"),
        (429, "http_429", "rate limited"),
    ],
)
def test_worker_returns_controlled_http_access_errors(
    monkeypatch, status_code: int, error_code: str, limitation: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="secret=response-body", request=request)

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/private?token=secret",
        normalized_url="https://example.test/private?token=secret",
    )

    LinkCheckWorker(transport=httpx.MockTransport(handler)).process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == error_code
    assert any(limitation in item for item in link_check.limitations)
    assert "secret" not in " ".join(link_check.limitations)
    assert link_check.links == []


def test_worker_maps_dns_failure_without_exposing_resolver_details(monkeypatch) -> None:
    def fail_dns(*_args, **_kwargs):
        raise socket.gaierror("resolver detail secret")

    monkeypatch.setattr("hidden_link_checker_api.scanner.ssrf.socket.getaddrinfo", fail_dns)
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://unresolved.example/?token=secret",
        normalized_url="https://unresolved.example/?token=secret",
    )

    LinkCheckWorker().process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "dns_resolution_failed"
    assert link_check.limitations == ["The URL host could not be resolved by DNS."]


def test_worker_maps_tls_error_without_exposing_exception_details(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        error = httpx.ConnectError("certificate detail secret", request=request)
        error.__cause__ = ssl.SSLError("private key secret")
        raise error

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/?token=secret",
        normalized_url="https://example.test/?token=secret",
    )

    LinkCheckWorker(transport=httpx.MockTransport(handler)).process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "tls_error"
    assert link_check.limitations == [
        "A secure TLS connection to the input page could not be established."
    ]


def test_worker_converts_parser_crash_to_safe_failed_result(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ok</html>", request=request)

    def fail_parser(*_args, **_kwargs):
        raise RuntimeError("parser secret detail")

    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.extract_findings", fail_parser
    )
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/",
        normalized_url="https://example.test/",
    )

    LinkCheckWorker(transport=httpx.MockTransport(handler)).process(link_check)

    assert link_check.status is LinkCheckStatus.FAILED
    assert link_check.error_code == "processing_failed"
    assert link_check.limitations == ["The input URL could not be processed."]
    assert "secret" not in " ".join(link_check.limitations)
