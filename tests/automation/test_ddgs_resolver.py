from unittest.mock import patch

from automation.models.fetch_result import FetchResult
from automation.resolvers.ddgs_resolver import (
    DDGSWebsiteResolver,
)


def test_resolver_rejects_empty_company_name():
    resolver = DDGSWebsiteResolver()

    result = resolver.resolve("")

    assert result.success is False
    assert result.website is None


@patch(
    "automation.resolvers.ddgs_resolver.fetch_website"
)
@patch(
    "automation.resolvers.ddgs_resolver.DDGS"
)
def test_resolver_selects_validated_official_site(
    mock_ddgs,
    mock_fetch_website,
):
    mock_ddgs.return_value.text.return_value = [
        {
            "title": "Example Company Directory",
            "href": (
                "https://unknown-directory.test/"
                "company/example"
            ),
            "body": "Business listing",
        },
        {
            "title": "Example Company",
            "href": "https://examplecompany.com/",
            "body": (
                "Example Company in Austin, Texas."
            ),
        },
    ]

    mock_fetch_website.return_value = FetchResult(
        success=True,
        final_url="https://examplecompany.com/",
        html="""
        <html>
            <head>
                <title>Example Company</title>
            </head>
            <body>
                <h1>Example Company</h1>
                <p>Austin, Texas</p>
            </body>
        </html>
        """,
        status_code=200,
    )

    resolver = DDGSWebsiteResolver(
        validation_limit=3,
        query_delay_seconds=0,
    )

    result = resolver.resolve(
        "Example Company LLC",
        "Austin, TX",
    )

    assert result.success is True
    assert result.website == (
        "https://examplecompany.com/"
    )

    mock_fetch_website.assert_called_once_with(
        "https://examplecompany.com/"
    )

    assert (
        "https://unknown-directory.test/company/example"
        in result.rejected_candidates
    )

    assert result.validated_candidates == [
        "https://examplecompany.com/",
    ]

@patch(
    "automation.resolvers.ddgs_resolver.fetch_website"
)
@patch(
    "automation.resolvers.ddgs_resolver.DDGS"
)

def test_resolver_skips_failed_candidate(
    mock_ddgs,
    mock_fetch_website,
):
    mock_ddgs.return_value.text.return_value = [
        {
            "title": "Example Company",
            "href": "https://examplecompany.com/",
            "body": "Official website",
        }
    ]

    mock_fetch_website.return_value = FetchResult(
        success=False,
        error="Connection failed",
    )

    resolver = DDGSWebsiteResolver()

    result = resolver.resolve(
        "Example Company LLC",
        "Austin, TX",
    )

    assert result.success is False


@patch(
    "automation.resolvers.ddgs_resolver.DDGS"
)
def test_resolver_rejects_known_directory(
    mock_ddgs,
):
    mock_ddgs.return_value.text.return_value = [
        {
            "title": "Carrier profile",
            "href": (
                "https://truckcarrierhub.com/"
                "GA/USDOT-111"
            ),
            "body": "Carrier directory",
        }
    ]

    resolver = DDGSWebsiteResolver()

    result = resolver.resolve(
        "Cain AM Bickley LLC",
        "Marshallville, GA",
    )

    assert result.success is False
    assert result.website is None