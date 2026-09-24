"""Extract supported DOM URLs without requesting or navigating to them."""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from hidden_link_checker_api.domain.models import ElementType, LinkResult, Visibility

BACKGROUND_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


class HiddenLinkExtractor(HTMLParser):
    """Parse text, image and inline-background URLs from an HTML document."""

    def __init__(self, link_check_id: object, final_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._link_check_id = link_check_id
        self._final_url = final_url
        self._links: list[LinkResult] = []
        self._anchor_href: str | None = None
        self._anchor_reference: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect URL-bearing attributes without navigating to their targets."""
        attributes = dict(attrs)
        object_reference = attributes.get("id") or tag
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_reference = object_reference
            self._anchor_text = []
        if tag == "img":
            self._add_image_links(attributes, object_reference)
        self._add_background_links(attributes.get("style"), object_reference)

    def handle_data(self, data: str) -> None:
        """Collect visible text nested inside a text anchor."""
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Create a direct text result when an anchor closes."""
        if tag != "a" or self._anchor_href is None:
            return
        visible_text = " ".join(part.strip() for part in self._anchor_text if part.strip())
        self._links.append(
            self._new_result(
                element_type=ElementType.TEXT,
                object_reference=self._anchor_reference,
                source_url=self._anchor_href,
                visibility=Visibility.DIRECT,
                visible_text=visible_text or None,
            )
        )
        self._anchor_href = None
        self._anchor_reference = None
        self._anchor_text = []

    def findings(self) -> list[LinkResult]:
        """Return the extracted results in DOM order."""
        return list(self._links)

    def _add_image_links(self, attributes: dict[str, str | None], object_reference: str) -> None:
        alt_text = attributes.get("alt")
        if attributes.get("src"):
            self._links.append(
                self._new_result(
                    element_type=ElementType.IMAGE,
                    object_reference=object_reference,
                    source_url=attributes["src"],
                    visibility=Visibility.INDIRECT,
                    alt_text=alt_text,
                )
            )
        for source_url in _parse_srcset(attributes.get("srcset")):
            self._links.append(
                self._new_result(
                    element_type=ElementType.IMAGE,
                    object_reference=object_reference,
                    source_url=source_url,
                    visibility=Visibility.INDIRECT,
                    alt_text=alt_text,
                )
            )

    def _add_background_links(self, style: str | None, object_reference: str) -> None:
        if not style:
            return
        for match in BACKGROUND_URL_PATTERN.finditer(style):
            source_url = match.group(2).strip()
            if source_url:
                self._links.append(
                    self._new_result(
                        element_type=ElementType.BACKGROUND,
                        object_reference=object_reference,
                        source_url=source_url,
                        visibility=Visibility.INDIRECT,
                    )
                )

    def _new_result(
        self,
        element_type: ElementType,
        object_reference: str | None,
        source_url: str,
        visibility: Visibility,
        visible_text: str | None = None,
        alt_text: str | None = None,
    ) -> LinkResult:
        return LinkResult(
            link_check_id=self._link_check_id,
            element_type=element_type,
            object_reference=object_reference,
            source_url=source_url,
            actual_url=urljoin(self._final_url, source_url),
            visibility=visibility,
            visible_text=visible_text,
            alt_text=alt_text,
        )


def extract_findings(html: str, final_url: str, link_check_id: object) -> list[LinkResult]:
    """Extract supported DOM URLs as data only; this function performs no I/O."""
    extractor = HiddenLinkExtractor(link_check_id=link_check_id, final_url=final_url)
    extractor.feed(html)
    extractor.close()
    return extractor.findings()


def _parse_srcset(srcset: str | None) -> list[str]:
    if not srcset:
        return []
    return [candidate.strip().split(maxsplit=1)[0] for candidate in srcset.split(",") if candidate.strip()]