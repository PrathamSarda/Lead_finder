from automation.enrichment.website_fetcher import (
    fetch_website,
    normalize_url,
)


def test_normalize_url_adds_https():
    assert normalize_url("example.com") == "https://example.com"


def test_normalize_url_preserves_https():
    assert normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_strips_whitespace():
    assert normalize_url("  example.com  ") == "https://example.com"


def test_normalize_url_rejects_empty_string():
    assert normalize_url("") is None


def test_fetch_website_rejects_empty_url():
    result = fetch_website("")

    assert result.success is False
    assert result.html is None
    assert result.error is not None


def test_fetch_website_downloads_html():
    result = fetch_website("https://example.com")

    assert result.success is True
    assert result.status_code == 200
    assert result.final_url is not None
    assert result.html is not None
    assert "<html" in result.html.lower()