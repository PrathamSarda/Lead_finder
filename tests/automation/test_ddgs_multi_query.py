from unittest.mock import patch

from automation.models.fetch_result import FetchResult
from automation.resolvers.ddgs_resolver import (
    DDGSWebsiteResolver,
    build_search_queries,
)


def test_build_search_queries_creates_fallbacks():
    queries = build_search_queries(
        company_name=(
            "Prairie Sand & Gravel Inc"
        ),
        location="Prairie Du Chien, WI",
    )

    assert len(queries) >= 3

    assert (
        '"Prairie Sand & Gravel Inc" '
        '"Prairie Du Chien, WI" website'
        in queries
    )

    assert any(
        "prairie sand gravel" in query.lower()
        for query in queries
    )


@patch(
    "automation.resolvers.ddgs_resolver.fetch_website"
)
@patch(
    "automation.resolvers.ddgs_resolver.DDGS"
)
def test_resolver_uses_later_query_when_first_fails(
    mock_ddgs,
    mock_fetch_website,
):
    mock_ddgs.return_value.text.side_effect = [
        [],
        [
            {
                "title": "Example Transport",
                "href": (
                    "https://exampletransport.com/"
                ),
                "body": (
                    "Example Transport in Dallas, Texas"
                ),
            }
        ],
        [],
        [],
    ]

    mock_fetch_website.return_value = FetchResult(
        success=True,
        final_url=(
            "https://exampletransport.com/"
        ),
        html="""
        <html>
            <head>
                <title>Example Transport</title>
            </head>
            <body>
                <h1>Example Transport</h1>
                Dallas, Texas
            </body>
        </html>
        """,
        status_code=200,
    )

    resolver = DDGSWebsiteResolver(
        query_delay_seconds=0,
    )

    result = resolver.resolve(
        company_name="Example Transport LLC",
        location="Dallas, TX",
    )

    assert result.success is True
    assert result.website == (
        "https://exampletransport.com/"
    )


@patch(
    "automation.resolvers.ddgs_resolver.fetch_website"
)
@patch(
    "automation.resolvers.ddgs_resolver.DDGS"
)
def test_duplicate_domains_are_validated_once(
    mock_ddgs,
    mock_fetch_website,
):
    mock_ddgs.return_value.text.side_effect = [
        [
            {
                "title": "Example Company",
                "href": (
                    "https://example.com/contact"
                ),
                "body": "Example Company contact",
            }
        ],
        [
            {
                "title": "Example Company Home",
                "href": "https://example.com/",
                "body": "Example Company homepage",
            }
        ],
        [],
        [],
    ]

    mock_fetch_website.return_value = FetchResult(
        success=True,
        final_url="https://example.com/",
        html="""
        <html>
            <title>Example Company</title>
            <body>
                <h1>Example Company</h1>
            </body>
        </html>
        """,
        status_code=200,
    )

    resolver = DDGSWebsiteResolver(
        query_delay_seconds=0,
    )

    result = resolver.resolve(
        company_name="Example Company LLC",
        location="Austin, TX",
    )

    assert result.success is True

    mock_fetch_website.assert_called_once_with(
        "https://example.com/"
    )


def test_resolver_rejects_negative_delay():
    try:
        DDGSWebsiteResolver(
            query_delay_seconds=-1,
        )
    except ValueError:
        assert True
    else:
        assert False