import re
from urllib.parse import urlparse


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

GENERIC_COMPANY_WORDS = {
    "and",
    "international",
    "group",
    "services",
    "service",
    "solutions",
    "enterprises",
    "enterprise",
    "industries",
    "industry",
}

EXCLUDED_DOMAINS = {
    "bbb.org",
    "bloomberg.com",
    "buzzfile.com",
    "chamberofcommerce.com",
    "crunchbase.com",
    "datastical.com",
    "dnb.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "loadwrap.com",
    "local.yahoo.com",
    "manta.com",
    "mapquest.com",
    "opencorporates.com",
    "quicktransportsolutions.com",
    "twitter.com",
    "x.com",
    "yellowpages.com",
    "yelp.com",
    "youtube.com",
    "zoominfo.com",
        "arktms.com",
    "carrier411.com",
    "findtruckservice.com",
    "freightconnect.com",
    "safer.fmcsa.dot.gov",
    "thetruckersreport.com",
    "truckcarrierhub.com",
    "truckcompaniesin.com",
    "truckingdatabase.com",
    "usdotlookup.com",
}

DIRECTORY_PATH_WORDS = {
    "business",
    "companies",
    "company",
    "directory",
    "listing",
    "profile",
    "transportation-company",
}

MIN_ACCEPTABLE_SCORE = 35


def _normalize_text(value: str | None) -> str:
    """
    Normalize text for comparison.
    """

    if not value:
        return ""

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    ).strip()


def _company_tokens(company_name: str) -> list[str]:
    """
    Return meaningful tokens from a legal company name.
    """

    tokens = re.findall(
        r"[a-z0-9]+",
        company_name.lower(),
    )

    meaningful_tokens = [
        token
        for token in tokens
        if token not in LEGAL_SUFFIXES
        and token not in GENERIC_COMPANY_WORDS
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


def _hostname(url: str) -> str:
    """
    Return a normalized hostname.
    """

    hostname = urlparse(url).netloc.lower()

    return hostname.removeprefix("www.")


def _is_excluded_domain(hostname: str) -> bool:
    """
    Check whether a hostname belongs to a known directory,
    aggregator, or social network.
    """

    return any(
        hostname == excluded_domain
        or hostname.endswith(f".{excluded_domain}")
        for excluded_domain in EXCLUDED_DOMAINS
    )


def score_search_result(
    company_name: str,
    location: str | None,
    title: str,
    url: str,
    description: str | None = None,
) -> int:
    """
    Score how likely a search result is to be the official website.

    Higher scores represent stronger official-domain confidence.
    Known directories and social networks receive a severe penalty.
    """

    hostname = _hostname(url)

    if not hostname:
        return -1_000

    if _is_excluded_domain(hostname):
        return -1_000

    parsed_url = urlparse(url)

    normalized_hostname = re.sub(
        r"[^a-z0-9]",
        "",
        hostname.split(".")[0],
    )

    normalized_title = _normalize_text(title)
    normalized_description = _normalize_text(description)
    normalized_location = _normalize_text(location)

    tokens = _company_tokens(company_name)

    if not tokens:
        return -1_000

    score = 0

    hostname_matches = sum(
        1
        for token in tokens
        if token in normalized_hostname
    )

    title_matches = sum(
        1
        for token in tokens
        if token in normalized_title
    )

    description_matches = sum(
        1
        for token in tokens
        if token in normalized_description
    )

    score += hostname_matches * 30
    score += title_matches * 12
    score += description_matches * 5

    joined_tokens = "".join(tokens)

    if joined_tokens and joined_tokens in normalized_hostname:
        score += 25

    if hostname_matches == len(tokens):
        score += 20

    if normalized_location:
        location_tokens = [
            token
            for token in normalized_location.split()
            if len(token) >= 2
        ]

        location_text = (
            f"{normalized_title} "
            f"{normalized_description}"
        )

        location_matches = sum(
            1
            for token in location_tokens
            if token in location_text
        )

        score += min(location_matches * 4, 12)

    path = parsed_url.path.lower()

    if any(
        path_word in path
        for path_word in DIRECTORY_PATH_WORDS
    ):
        score -= 25

    if path in {"", "/"}:
        score += 10

    if "official" in normalized_title:
        score += 5

    return score