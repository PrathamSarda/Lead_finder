import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


LEGAL_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "llp",
    "lp",
    "ltd",
    "limited",
    "pllc",
}

GENERIC_WORDS = {
    "and",
    "group",
    "international",
    "industries",
    "industry",
    "services",
    "service",
    "solutions",
    "enterprises",
    "enterprise",
}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    ).strip()


def _company_tokens(company_name: str) -> list[str]:
    tokens = re.findall(
        r"[a-z0-9]+",
        company_name.lower(),
    )

    meaningful_tokens = [
        token
        for token in tokens
        if token not in LEGAL_SUFFIXES
        and token not in GENERIC_WORDS
        and len(token) >= 3
    ]

    if meaningful_tokens:
        return meaningful_tokens

    return [
        token
        for token in tokens
        if token not in LEGAL_SUFFIXES
        and len(token) >= 2
    ]


def _hostname_text(url: str) -> str:
    hostname = (
        urlparse(url)
        .netloc
        .lower()
        .removeprefix("www.")
    )

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        hostname,
    ).strip()


def validate_company_homepage(
    company_name: str,
    location: str | None,
    url: str,
    html: str,
) -> bool:
    """
    Determine whether a root homepage likely belongs to the company.

    A company appearing only in general page text is not sufficient.
    The hostname, page title, or primary headings must provide a
    strong ownership signal.
    """

    if not html.strip():
        return False

    company_tokens = _company_tokens(company_name)

    if not company_tokens:
        return False

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    heading_text = " ".join(
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(
            ["h1", "h2"],
            limit=8,
        )
    )

    page_text = soup.get_text(
        " ",
        strip=True,
    )[:20_000]

    hostname_text = _hostname_text(url)

    normalized_title = _normalize_text(title)
    normalized_headings = _normalize_text(
        heading_text
    )
    normalized_page_text = _normalize_text(
        page_text
    )

    hostname_matches = {
        token
        for token in company_tokens
        if token in hostname_text
    }

    title_matches = {
        token
        for token in company_tokens
        if token in normalized_title
    }

    heading_matches = {
        token
        for token in company_tokens
        if token in normalized_headings
    }

    page_matches = {
        token
        for token in company_tokens
        if token in normalized_page_text
    }

    strong_matches = (
        hostname_matches
        | title_matches
        | heading_matches
    )

    if len(company_tokens) == 1:
        token = company_tokens[0]

        return (
            token in hostname_text
            or token in normalized_title
            or token in normalized_headings
        )

    # Strong official-domain signal.
    if len(hostname_matches) >= 2:
        return True

    # Company is clearly branded in title or primary headings.
    if len(title_matches | heading_matches) >= 2:
        return True

    # One hostname token plus strong branding elsewhere.
    if (
        len(hostname_matches) >= 1
        and len(title_matches | heading_matches) >= 1
        and len(strong_matches) >= 2
    ):
        return True

    # Page-body mentions alone must never validate ownership.
    if not hostname_matches and not title_matches and not heading_matches:
        return False

    location_text = _normalize_text(location)

    if location_text:
        location_tokens = [
            token
            for token in location_text.split()
            if len(token) >= 2
        ]

        location_matches = sum(
            1
            for token in location_tokens
            if token in normalized_page_text
        )

        if (
            len(strong_matches) >= 2
            and len(page_matches) >= 2
            and location_matches >= 1
        ):
            return True

    return False