from uuid import uuid4

import httpx

from hidden_link_checker_api.domain.models import LinkCheck, LinkCheckStatus
from hidden_link_checker_api.repositories.link_checks import InMemoryLinkCheckRepository
from hidden_link_checker_api.workers.link_check_worker import LinkCheckWorker


def test_worker_fetches_input_and_extracts_hidden_links_without_following_findings(monkeypatch):
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                '<a href="/about">About</a>'
                '<img src="/hero.png" srcset="/hero@2x.png 2x" alt="Hero">'
                '<div style="background-image: url(\'/offer.png\')"></div>'
            ),
            request=request,
        )

    repository = InMemoryLinkCheckRepository()
    link_check = LinkCheck(
        user_id=uuid4(),
        submitted_url="https://example.test/home",
        normalized_url="https://example.test/home",
        include_dom=True,
    )
    repository.add(link_check)
    monkeypatch.setattr(
        "hidden_link_checker_api.workers.link_check_worker.ensure_safe_navigation_url",
        lambda url: url,
    )
    worker = LinkCheckWorker(repository, transport=httpx.MockTransport(handler))

    worker.process(link_check.id)

    persisted = repository.get_by_id(link_check.id)
    assert persisted is not None
    assert persisted.status is LinkCheckStatus.COMPLETED
    assert [result.actual_url for result in persisted.links] == [
        "https://example.test/about",
        "https://example.test/hero.png",
        "https://example.test/hero@2x.png",
        "https://example.test/offer.png",
    ]
    assert requested_urls == ["https://example.test/home"]
