import pytest

from hidden_link_checker_api.scanner.urls import InvalidInputUrlError, normalize_input_url


def test_normalize_input_url_accepts_absolute_https_url() -> None:
    assert normalize_input_url(" HTTPS://Example.COM/path#section ") == "https://example.com/path"


@pytest.mark.parametrize("submitted_url", ["ftp://example.com", "/relative", "https:///missing-host"])
def test_normalize_input_url_rejects_unsupported_or_relative_urls(submitted_url: str) -> None:
    with pytest.raises(InvalidInputUrlError):
        normalize_input_url(submitted_url)