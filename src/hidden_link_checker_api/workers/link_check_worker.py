"""Fetch submitted pages safely and extract their hidden links."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import BoundedSemaphore
from time import monotonic

import httpx

from hidden_link_checker_api.domain.models import LinkCheck, LinkCheckStatus
from hidden_link_checker_api.scanner.browser_renderer import BrowserPageRenderer
from hidden_link_checker_api.scanner.extractor import extract_findings
from hidden_link_checker_api.scanner.fetcher import BoundedUrlFetcher, LinkCheckFetchError
from hidden_link_checker_api.scanner.ssrf import (
    UnsafeNavigationUrlError,
    ensure_safe_navigation_url,
)
from hidden_link_checker_api.scanner.urls import InvalidInputUrlError

MAX_DOM_EXCERPT_CHARACTERS = 12_000


class LinkCheckWorker:
    """Synchronously fetch the submitted URL; findings are never navigated to."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        max_redirects: int = 5,
        max_response_bytes: int = 2 * 1024 * 1024,
        max_concurrent: int = 4,
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
            link_check.limitations.append("The URL check exceeded the configured concurrency limit.")
            link_check.error_code = "timeout"
            link_check.status = LinkCheckStatus.FAILED
            link_check.completed_at = datetime.now(UTC)
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
            UnsafeNavigationUrlError,
            httpx.HTTPError,
            LinkCheckFetchError,
        ) as error:
            link_check.limitations.append(str(error))
            link_check.error_code = _error_code(error)
            link_check.status = LinkCheckStatus.FAILED
        except Exception:  # noqa: BLE001 - convert unexpected worker failures to controlled results.
            link_check.limitations.append("The input URL could not be processed.")
            link_check.error_code = "processing_failed"
            link_check.status = LinkCheckStatus.FAILED
        finally:
            self._slots.release()
            link_check.completed_at = datetime.now(UTC)


def _error_code(error: Exception) -> str:
    if isinstance(error, UnsafeNavigationUrlError):
        return "unsafe_navigation_url"
    if isinstance(error, InvalidInputUrlError):
        return "invalid_input_url"
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return f"http_{error.response.status_code}"
    return "fetch_failed"
