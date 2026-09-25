"""Fetch submitted pages safely and extract their hidden links."""

from __future__ import annotations

import ssl
from threading import BoundedSemaphore
from time import monotonic

import httpx

from hidden_link_checker_api.domain.models import LinkCheck, LinkCheckStatus
from hidden_link_checker_api.scanner.browser_renderer import BrowserPageRenderer
from hidden_link_checker_api.scanner.extractor import extract_findings
from hidden_link_checker_api.scanner.fetcher import (
    BoundedUrlFetcher,
    FetchLimitError,
    LinkCheckFetchError,
)
from hidden_link_checker_api.scanner.ssrf import (
    NavigationDnsError,
    UnsafeNavigationUrlError,
    ensure_safe_navigation_url,
)
from hidden_link_checker_api.scanner.urls import InvalidInputUrlError
from hidden_link_checker_api.scan_limits import (
    DEFAULT_SCAN_MAX_CONCURRENT,
    DEFAULT_SCAN_MAX_REDIRECTS,
    DEFAULT_SCAN_MAX_RESPONSE_BYTES,
    DEFAULT_SCAN_TIMEOUT_SECONDS,
)

MAX_DOM_EXCERPT_CHARACTERS = 12_000


class LinkCheckWorker:
    """Synchronously fetch the submitted URL; findings are never navigated to."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = DEFAULT_SCAN_TIMEOUT_SECONDS,
        max_redirects: int = DEFAULT_SCAN_MAX_REDIRECTS,
        max_response_bytes: int = DEFAULT_SCAN_MAX_RESPONSE_BYTES,
        max_concurrent: int = DEFAULT_SCAN_MAX_CONCURRENT,
        renderer: BrowserPageRenderer | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._slots = BoundedSemaphore(max_concurrent)
        self._renderer = renderer or BrowserPageRenderer(timeout_seconds=timeout_seconds)
        self._fetcher = BoundedUrlFetcher(
            transport=transport,
            max_redirects=max_redirects,
            max_response_bytes=max_response_bytes,
            safe_url_validator=ensure_safe_navigation_url,
        )

    def process(self, link_check: LinkCheck) -> None:
        """Fetch only the submitted page and attach findings to this request object."""
        deadline = monotonic() + self._timeout
        if not self._slots.acquire(timeout=self._timeout):
            link_check.limitations.append(
                "The check could not start because the service reached its concurrency limit."
            )
            link_check.error_code = "concurrency_limit"
            link_check.status = LinkCheckStatus.FAILED
            return
        try:
            fetched = self._fetcher.fetch(link_check.normalized_url, deadline)
            remaining_seconds = deadline - monotonic()
            if remaining_seconds <= 0:
                raise httpx.TimeoutException("The URL check exceeded its configured timeout.")
            rendered = self._renderer.render(
                fetched.html, fetched.final_url, timeout_seconds=remaining_seconds
            )
            html = rendered.html
            limitations = fetched.limitations + list(rendered.limitations)
            rendered_size = len(html.encode("utf-8"))
            if rendered_size > self._max_response_bytes:
                html = html.encode("utf-8")[: self._max_response_bytes].decode(
                    "utf-8", errors="ignore"
                )
                limitations.append("The rendered DOM exceeded the configured size limit and was truncated.")
            link_check.final_url = fetched.final_url
            link_check.http_status = fetched.http_status
            link_check.links = extract_findings(html, fetched.final_url)
            link_check.dom_excerpt = html[:MAX_DOM_EXCERPT_CHARACTERS]
            if len(html) > MAX_DOM_EXCERPT_CHARACTERS:
                limitations.append("The displayed DOM excerpt was truncated.")
            link_check.limitations.extend(limitations)
            link_check.status = LinkCheckStatus.PARTIAL if limitations else LinkCheckStatus.COMPLETED
        except (
            InvalidInputUrlError,
            NavigationDnsError,
            UnsafeNavigationUrlError,
            ssl.SSLError,
            httpx.HTTPError,
            LinkCheckFetchError,
        ) as error:
            link_check.limitations.append(_safe_limitation(error))
            link_check.error_code = _error_code(error)
            link_check.status = LinkCheckStatus.FAILED
        except Exception:  # noqa: BLE001 - convert unexpected worker failures to controlled results.
            link_check.limitations.append("The input URL could not be processed.")
            link_check.error_code = "processing_failed"
            link_check.status = LinkCheckStatus.FAILED
        finally:
            self._slots.release()


def _error_code(error: Exception) -> str:
    if isinstance(error, InvalidInputUrlError):
        return "invalid_input_url"
    if isinstance(error, NavigationDnsError):
        return "dns_resolution_failed"
    if isinstance(error, UnsafeNavigationUrlError):
        return "unsafe_navigation_url"
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return f"http_{error.response.status_code}"
    if isinstance(error, FetchLimitError):
        return "resource_limit_exceeded"
    if _is_tls_error(error):
        return "tls_error"
    return "fetch_failed"


def _safe_limitation(error: Exception) -> str:
    """Return user-facing diagnostic text without echoing request or exception data."""
    if isinstance(error, InvalidInputUrlError):
        return str(error)
    if isinstance(error, NavigationDnsError):
        return "The URL host could not be resolved by DNS."
    if isinstance(error, UnsafeNavigationUrlError):
        return str(error)
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        if status_code == 403:
            return "The input page denied access with HTTP 403."
        if status_code == 429:
            return "The input page rate limited the request with HTTP 429."
        return f"The input page returned HTTP {status_code}."
    if isinstance(error, httpx.TimeoutException):
        return "The input page could not be fetched within the configured time limit."
    if isinstance(error, FetchLimitError):
        return str(error)
    if _is_tls_error(error):
        return "A secure TLS connection to the input page could not be established."
    if isinstance(error, LinkCheckFetchError):
        return str(error)
    return "The input page could not be fetched because of a network error."


def _is_tls_error(error: Exception) -> bool:
    """Detect TLS failures while keeping their raw exception text out of responses."""
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        if isinstance(current, ssl.SSLError):
            return True
        visited.add(id(current))
        current = current.__cause__ or current.__context__
    return False
