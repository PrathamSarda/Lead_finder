from __future__ import annotations

import re
from difflib import SequenceMatcher
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
    "pc",
    "group",
    "holdings",
}


COMMON_DOMAIN_PREFIXES = {
    "www",
    "the",
    "official",
}


def _tokenize(value: str) -> list[str]:
    """Convert a string into lowercase alphanumeric tokens."""

    return re.findall(r"[a-z0-9]+", value.lower())


def normalize_company_name(company_name: str) -> str:
    """
    Normalize a company name for comparison with a domain.

    Example:
        CWT FARMS INTERNATIONAL INC
        -> cwtfarmsinternational
    """

    tokens = [
        token
        for token in _tokenize(company_name)
        if token not in LEGAL_SUFFIXES
    ]

    return "".join(tokens)


def extract_domain_name(url: str) -> str:
    """
    Extract the meaningful domain portion from a URL.

    Examples:
        https://www.biolabinc.com/about
        -> biolabinc

        https://cwtfarmsinternational.com/
        -> cwtfarmsinternational
    """

    try:
        hostname = urlparse(url).hostname or ""
    except ValueError:
        return ""

    hostname = hostname.lower().strip(".")

    if not hostname:
        return ""

    parts = hostname.split(".")

    if parts and parts[0] in COMMON_DOMAIN_PREFIXES:
        parts = parts[1:]

    if not parts:
        return ""

    # This intentionally takes the primary domain label.
    # It is sufficient for the current US-company resolver.
    return re.sub(r"[^a-z0-9]", "", parts[0])


def calculate_domain_similarity(
    company_name: str,
    url: str,
) -> float:
    """
    Return a similarity value between 0.0 and 1.0.
    """

    raw_company = "".join(_tokenize(company_name))
    normalized_company = normalize_company_name(company_name)
    normalized_domain = extract_domain_name(url)

    if not normalized_company or not normalized_domain:
        return 0.0

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    tld = host.split(".")[-1]
    foreign_cctlds = {
        "jo", "ru", "cn", "in", "pk", "ir", "by", "vn", "br", "ng", "za", "tr", "ua", "kz", "sa", "eg"
    }
    if tld in foreign_cctlds:
        return 0.10

    if raw_company == normalized_domain or normalized_company == normalized_domain:
        return 1.0

    if raw_company in normalized_domain or normalized_company in normalized_domain:
        return 0.95

    if normalized_domain in raw_company or normalized_domain in normalized_company:
        domain_coverage = (
            len(normalized_domain)
            / len(normalized_company)
        )

        # Avoid rewarding tiny generic domains such as "abc".
        if domain_coverage >= 0.55:
            return max(0.80, domain_coverage)

    sim1 = SequenceMatcher(None, normalized_company, normalized_domain).ratio()
    sim2 = SequenceMatcher(None, raw_company, normalized_domain).ratio()
    return max(sim1, sim2)


def calculate_domain_bonus(
    company_name: str,
    url: str,
) -> int:
    """
    Convert domain similarity into a resolver score bonus.

    A strong company-domain match should substantially outrank
    unrelated news, directory, government, and association sites.
    """

    similarity = calculate_domain_similarity(
        company_name=company_name,
        url=url,
    )

    if similarity >= 0.95:
        return 120

    if similarity >= 0.85:
        return 90

    if similarity >= 0.75:
        return 60

    if similarity >= 0.65:
        return 35

    if similarity >= 0.55:
        return 15

    return 0