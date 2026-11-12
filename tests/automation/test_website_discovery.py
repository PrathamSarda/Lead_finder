from unittest.mock import patch

from automation.enrichment.website_discovery import (
    discover_company_website,
    generate_domain_candidates,
)
from automation.models.fetch_result import FetchResult


def test_generate_domain_candidates():
    candidates = generate_domain_candidates(
        "Dixon Paving Corporation"
    )

    assert "https://dixonpaving.com" in candidates
    assert "https://dixonpaving.net" in candidates
    assert "https://dixonpaving.co" in candidates
    assert (
        "https://dixon-paving.com"
        in candidates
    )


def test_generate_domain_candidates_removes_legal_suffixes():
    candidates = generate_domain_candidates(
        "Example Logistics LLC"
    )

    assert (
        "https://examplelogistics.com"
        in candidates
    )

    assert all(
        "llc" not in candidate
        for candidate in candidates
    )


@patch(
    "automation.enrichment.website_discovery.fetch_website"
)
def test_discover_company_website_returns_matching_site(
    mock_fetch_website,
):
    mock_fetch_website.return_value = FetchResult(
        success=True,
        final_url="https://dixonpaving.com",
        html="""
        <html>
            <head>
                <title>Dixon Paving</title>
            </head>
            <body>
                Dixon Paving provides asphalt and paving services.
            </body>
        </html>
        """,
        status_code=200,
    )

    result = discover_company_website(
        "Dixon Paving Corporation"
    )

    assert result.success is True
    assert result.website == (
        "https://dixonpaving.com"
    )


@patch(
    "automation.enrichment.website_discovery.fetch_website"
)
def test_discovery_skips_failed_candidates(
    mock_fetch_website,
):
    mock_fetch_website.return_value = FetchResult(
        success=False,
        error="Connection failed",
    )

    result = discover_company_website(
        "Unknown Carrier LLC"
    )

    assert result.success is False
    assert result.website is None
    assert result.checked_candidates


def test_discovery_rejects_empty_company_name():
    result = discover_company_website("")

    assert result.success is False
    assert result.website is None