from hidden_link_checker_api.domain.models import ElementType, Visibility
from hidden_link_checker_api.scanner.extractor import extract_findings


def test_extract_findings_resolves_text_image_srcset_and_background_urls() -> None:
    html = """
    <a id="about" href="/about">About us</a>
    <img id="hero" src="/hero.png" srcset="/hero@2x.png 2x" alt="Hero">
    <div id="offer" style="background-image: url('/offer.png')"></div>
    """

    results = extract_findings(html, "https://example.test/home")

    assert [(result.element_type, result.visibility) for result in results] == [
        (ElementType.TEXT, Visibility.DIRECT),
        (ElementType.IMAGE, Visibility.INDIRECT),
        (ElementType.IMAGE, Visibility.INDIRECT),
        (ElementType.BACKGROUND, Visibility.INDIRECT),
    ]
    assert [result.actual_url for result in results] == [
        "https://example.test/about",
        "https://example.test/hero.png",
        "https://example.test/hero@2x.png",
        "https://example.test/offer.png",
    ]
    assert results[0].visible_text == "About us"
    assert results[1].alt_text == "Hero"
