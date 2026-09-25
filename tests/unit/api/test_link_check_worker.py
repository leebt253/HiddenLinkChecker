from uuid import uuid4

import httpx

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
