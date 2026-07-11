from unittest.mock import patch

from automation.enrichment.company_enricher import enrich_company
from automation.models.fetch_result import FetchResult


@patch(
    "automation.enrichment.company_enricher.fetch_website"
)
def test_homepage_failure_returns_failed_result(
    mock_fetch_website,
):
    mock_fetch_website.return_value = FetchResult(
        success=False,
        final_url="https://company.com",
        error="Connection failed",
    )

    result = enrich_company("https://company.com")

    assert result.success is False
    assert result.error == "Connection failed"
    assert result.emails == []
    assert result.phone_numbers == []
    assert result.contact_pages == []


@patch(
    "automation.enrichment.company_enricher.find_contact_pages"
)
@patch(
    "automation.enrichment.company_enricher.fetch_website"
)
def test_enrich_company_merges_homepage_and_contact_page_data(
    mock_fetch_website,
    mock_find_contact_pages,
):
    homepage_html = """
    <html>
        <body>
            <p>Email: info@company.com</p>
            <p>Phone: (212) 555-0123</p>
        </body>
    </html>
    """

    contact_html = """
    <html>
        <body>
            <p>Email: sales@company.com</p>
            <p>Phone: (415) 555-2671</p>
        </body>
    </html>
    """

    mock_fetch_website.side_effect = [
        FetchResult(
            success=True,
            final_url="https://company.com",
            html=homepage_html,
            status_code=200,
        ),
        FetchResult(
            success=True,
            final_url="https://company.com/contact",
            html=contact_html,
            status_code=200,
        ),
    ]

    mock_find_contact_pages.return_value = [
        "https://company.com/contact",
    ]

    result = enrich_company("https://company.com")

    assert result.success is True
    assert result.homepage_url == "https://company.com"

    assert result.emails == [
        "info@company.com",
        "sales@company.com",
    ]

    assert result.phone_numbers == [
        "+12125550123",
        "+14155552671",
    ]

    assert result.contact_pages == [
        "https://company.com/contact",
    ]

    assert result.fetched_pages == [
        "https://company.com",
        "https://company.com/contact",
    ]

    assert result.failed_pages == []


@patch(
    "automation.enrichment.company_enricher.find_contact_pages"
)
@patch(
    "automation.enrichment.company_enricher.fetch_website"
)
def test_contact_page_failure_does_not_fail_entire_enrichment(
    mock_fetch_website,
    mock_find_contact_pages,
):
    mock_fetch_website.side_effect = [
        FetchResult(
            success=True,
            final_url="https://company.com",
            html="<p>Email: info@company.com</p>",
            status_code=200,
        ),
        FetchResult(
            success=False,
            final_url="https://company.com/contact",
            status_code=500,
            error="Server error",
        ),
    ]

    mock_find_contact_pages.return_value = [
        "https://company.com/contact",
    ]

    result = enrich_company("https://company.com")

    assert result.success is True

    assert result.emails == [
        "info@company.com",
    ]

    assert result.failed_pages == [
        "https://company.com/contact",
    ]


@patch(
    "automation.enrichment.company_enricher.find_contact_pages"
)
@patch(
    "automation.enrichment.company_enricher.fetch_website"
)
def test_duplicate_contact_information_is_removed(
    mock_fetch_website,
    mock_find_contact_pages,
):
    duplicate_html = """
    <p>Email: info@company.com</p>
    <p>Phone: (212) 555-0123</p>
    """

    mock_fetch_website.side_effect = [
        FetchResult(
            success=True,
            final_url="https://company.com",
            html=duplicate_html,
            status_code=200,
        ),
        FetchResult(
            success=True,
            final_url="https://company.com/contact",
            html=duplicate_html,
            status_code=200,
        ),
    ]

    mock_find_contact_pages.return_value = [
        "https://company.com/contact",
    ]

    result = enrich_company("https://company.com")

    assert result.emails == [
        "info@company.com",
    ]

    assert result.phone_numbers == [
        "+12125550123",
    ]