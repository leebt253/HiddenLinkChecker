"""Fetch submitted pages safely and extract their hidden links."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin
from uuid import UUID

import httpx

from hidden_link_checker_api.domain.models import LinkCheckStatus
from hidden_link_checker_api.repositories.link_checks import LinkCheckRepository
from hidden_link_checker_api.scanner.extractor import extract_findings
from hidden_link_checker_api.scanner.ssrf import (
    UnsafeNavigationUrlError,
    ensure_safe_navigation_url,
)
from hidden_link_checker_api.scanner.urls import InvalidInputUrlError


class LinkCheckFetchError(RuntimeError):
    """Raised when the submitted page cannot produce a usable document."""


class LinkCheckWorker:
    """Process one link check without ever requesting discovered hidden links."""

    def __init__(
        self,
        repository: LinkCheckRepository,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        max_redirects: int = 5,
        max_response_bytes: int = 2 * 1024 * 1024,
    ) -> None:
        self._repository = repository
        self._transport = transport
        self._timeout = timeout_seconds
        self._max_redirects = max_redirects
        self._max_response_bytes = max_response_bytes

    def process(self, check_id: UUID) -> None:
        """Fetch and parse a queued check, recording a controlled lifecycle result."""
        link_check = self._repository.get_by_id(check_id)
        if link_check is None:
            return
        link_check.status = LinkCheckStatus.RUNNING
        try:
            html, final_url, http_status, limitations = self._fetch_document(link_check.normalized_url)
            link_check.final_url = final_url
            link_check.http_status = http_status
            link_check.links = extract_findings(html, final_url, link_check.id)
            link_check.dom_reference = f"inline:{link_check.id}" if link_check.include_dom else None
            link_check.limitations.extend(limitations)
            link_check.status = LinkCheckStatus.PARTIAL if limitations else LinkCheckStatus.COMPLETED
        except (InvalidInputUrlError, UnsafeNavigationUrlError, httpx.HTTPError, LinkCheckFetchError) as error:
            link_check.limitations.append(str(error))
            link_check.error_code = _error_code(error)
            link_check.status = LinkCheckStatus.FAILED
        finally:
            link_check.completed_at = datetime.now(UTC)
            save_processed = getattr(self._repository, "save_processed", None)
            if save_processed is not None:
                save_processed(link_check)

    def _fetch_document(self, submitted_url: str) -> tuple[str, str, int, list[str]]:
        current_url = ensure_safe_navigation_url(submitted_url)
        limitations: list[str] = []
        with httpx.Client(
            follow_redirects=False,
            timeout=self._timeout,
            trust_env=False,
            transport=self._transport,
            headers={"User-Agent": "HiddenLinkChecker/0.1"},
        ) as client:
            for redirect_count in range(self._max_redirects + 1):
                with client.stream("GET", current_url) as response:
                    if 300 <= response.status_code < 400:
                        location = response.headers.get("location")
                        if not location:
                            raise LinkCheckFetchError("The input URL returned a redirect without a location.")
                        if redirect_count == self._max_redirects:
                            raise LinkCheckFetchError("The input URL exceeded the redirect limit.")
                        current_url = ensure_safe_navigation_url(urljoin(current_url, location))
                        continue
                    if response.status_code >= 400:
                        raise httpx.HTTPStatusError(
                            f"The input URL returned HTTP {response.status_code}.",
                            request=response.request,
                            response=response,
                        )
                    content = self._read_limited_body(response)
                    content_type = response.headers.get("content-type", "")
                    if content_type and "html" not in content_type.lower():
                        limitations.append("The response content type is not HTML.")
                    return (
                        content.decode(response.encoding or "utf-8", errors="replace"),
                        current_url,
                        response.status_code,
                        limitations,
                    )
        raise LinkCheckFetchError("The input URL could not be fetched.")

    def _read_limited_body(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        total_bytes = 0
        for chunk in response.iter_bytes():
            total_bytes += len(chunk)
            if total_bytes > self._max_response_bytes:
                raise LinkCheckFetchError("The response exceeded the configured size limit.")
            chunks.append(chunk)
        return b"".join(chunks)


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