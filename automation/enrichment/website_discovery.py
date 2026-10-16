import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from automation.enrichment.website_fetcher import fetch_website
from automation.models.website_discovery_result import (
    WebsiteDiscoveryResult,
)


LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "pllc",
    "lp",
    "llp",
}

DEFAULT_TLDS = (
    ".com",
    ".net",
    ".co",
)


def _tokenize_company_name(
    company_name: str,
) -> list[str]:
    """
    Convert a company name into useful domain tokens.
    """

    tokens = re.findall(
        r"[a-z0-9]+",
        company_name.lower(),
    )

    return [
        token
        for token in tokens
        if token not in LEGAL_SUFFIXES
    ]


def generate_domain_candidates(
    company_name: str,
) -> list[str]:
    """
    Generate likely official website URLs from a company name.
    """

    if not isinstance(company_name, str):
        return []

    tokens = _tokenize_company_name(company_name)

    if not tokens:
        return []

    joined_name = "".join(tokens)
    hyphenated_name = "-".join(tokens)

    domain_names = [
        joined_name,
        hyphenated_name,
    ]

    candidates = []

    for domain_name in (joined_name, hyphenated_name):
        for tld in DEFAULT_TLDS:
            candidate = f"https://{domain_name}{tld}"
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


def _extract_page_text(html: str) -> str:
    """
    Extract normalized visible text from HTML.
    """

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    return soup.get_text(
        " ",
        strip=True,
    ).lower()


def _matches_company(
    company_name: str,
    html: str,
    final_url: str,
) -> bool:
    """
    Check whether a fetched website appears to belong to the company.
    """

    company_tokens = _tokenize_company_name(
        company_name
    )

    if not company_tokens:
        return False

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    headings = " ".join(
        h.get_text(" ", strip=True).lower()
        for h in soup.find_all(["h1", "h2"], limit=4)
    )

    hostname = (
        urlparse(final_url)
        .netloc
        .lower()
        .removeprefix("www.")
    )

    # Check hostname match: at least one token must be in hostname
    joined_name = "".join(company_tokens)
    hostname_clean = re.sub(r"[^a-z0-9]", "", hostname.split(".")[0])

    if joined_name in hostname_clean or hostname_clean in joined_name:
        return True

    # Otherwise check title and headings for company tokens
    branding_text = f"{title} {headings}"
    matched_in_branding = sum(
        1 for token in company_tokens if token in branding_text
    )

    required = len(company_tokens) if len(company_tokens) <= 2 else len(company_tokens) - 1
    return matched_in_branding >= max(1, required)


def discover_company_website(
    company_name: str,
) -> WebsiteDiscoveryResult:
    """
    Discover and validate a likely official company website.

    The function generates a limited set of domain candidates and
    validates each candidate using the existing website fetcher.
    """

    candidates = generate_domain_candidates(
        company_name
    )

    if not candidates:
        return WebsiteDiscoveryResult(
            success=False,
            error=(
                "No website candidates could be generated "
                "from the company name."
            ),
        )

    checked_candidates = []

    for candidate in candidates:
        checked_candidates.append(candidate)

        fetch_result = fetch_website(candidate, timeout=4)

        if not fetch_result.success:
            continue

        html = fetch_result.html or ""
        final_url = (
            fetch_result.final_url
            or candidate
        )

        if _matches_company(
            company_name=company_name,
            html=html,
            final_url=final_url,
        ):
            return WebsiteDiscoveryResult(
                success=True,
                website=final_url,
                checked_candidates=checked_candidates,
            )

    return WebsiteDiscoveryResult(
        success=False,
        checked_candidates=checked_candidates,
        error="No validated company website was found.",
    )