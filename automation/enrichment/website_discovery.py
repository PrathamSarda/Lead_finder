import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from automation.enrichment.website_fetcher import fetch_website
from automation.models.website_discovery_result import (
    WebsiteDiscoveryResult,
)
from automation.verification.directory_registry import (
    is_directory_domain,
    normalize_domain,
)

# Signals that indicate a personal / author / blog / entertainment site (not a business)
_PERSONAL_SIGNALS = {
    "author", "novelist", "fiction", "nonfiction", "non-fiction",
    "mystery", "thriller", "romance", "biography", "memoir",
    "espionage", "spy novel", "bestseller", "blog", "poetry",
    "freelance writer", "illustrator", "screenwriter",
    "musician", "jazz", "trio", "pianist", "guitarist", "recording artist",
    "discography", "live concerts", "tour dates", "album release", "stream music",
}
# Signals that confirm a legitimate business
_BUSINESS_SIGNALS = {
    "freight", "trucking", "carrier", "transport", "logistics",
    "shipping", "delivery", "dispatch", "fleet", "truck",
    "bleach", "chemical", "manufacturing", "industrial",
    "distributor", "wholesale", "our services", "contact us",
    "request a quote", "about us", "our team", "our company",
    "equipment", "contractor", "construction",
}


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
    ".org",
    ".us",
    ".biz",
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
    state: str | None = None,
    include_legal_suffix: bool = False,
) -> list[str]:
    """
    Generate likely official website URLs from a company name.

    Also tries state-specific patterns (e.g., companyname-tx.com)
    and full legal name patterns when requested.
    """

    if not isinstance(company_name, str):
        return []

    tokens = _tokenize_company_name(company_name)

    if not tokens:
        return []

    joined_name = "".join(tokens)
    hyphenated_name = "-".join(tokens)

    candidates = []

    # 1. First priority: .com domains (most common for US commercial businesses)
    # Both without legal suffix (biolab.com) and with legal suffix (biolabinc.com)
    candidates.append(f"https://{joined_name}.com")

    all_raw_tokens = re.findall(r"[a-z0-9]+", company_name.lower())
    if include_legal_suffix and all_raw_tokens != tokens:
        raw_joined = "".join(all_raw_tokens)
        candidates.append(f"https://{raw_joined}.com")

    candidates.append(f"https://{hyphenated_name}.com")

    # State-suffixed .com (e.g. companyname-tx.com)
    if state:
        state_lower = state.strip().lower()
        if len(state_lower) == 2:
            candidates.append(f"https://{joined_name}{state_lower}.com")
            candidates.append(f"https://{joined_name}-{state_lower}.com")

    # 2. Secondary priority: .net, .co, .org, .us
    for tld in (".net", ".us", ".org", ".co", ".biz"):
        candidates.append(f"https://{joined_name}{tld}")
        if include_legal_suffix and all_raw_tokens != tokens:
            candidates.append(f"https://{''.join(all_raw_tokens)}{tld}")
        candidates.append(f"https://{hyphenated_name}{tld}")

    # Remove duplicates while preserving exact priority order
    return list(dict.fromkeys(candidates))


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


def _looks_like_personal_name(company_name: str) -> bool:
    """
    Return True when the company name looks like a personal first-last name.
    e.g. 'Glen Dyer', 'Richard Austin'
    """
    tokens = re.findall(r"[a-z]+", company_name.lower())
    meaningful = [t for t in tokens if t not in LEGAL_SUFFIXES and len(t) >= 2]
    return len(meaningful) == 2 and all(2 <= len(t) <= 15 for t in meaningful)


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

    # Reject known directory/lookup domains (e.g. zip-codes.com after redirect)
    if is_directory_domain(normalize_domain(final_url)):
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

    # Check for parked domain or domain-for-sale indicators
    lower_html = html.lower()
    parked_indicators = (
        "domain for sale",
        "buy this domain",
        "is for sale",
        "this domain may be for sale",
        "inquire about this domain",
        "domain has expired",
        "hugedomains.com",
        "dan.com",
        "sedoparking.com",
        "afternic.com",
        "parked domain",
        "godaddy parked",
        "listed with spaceship.com",
        "free transaction support",
        "make offer",
        "buy now",
        "fatal error",
        "parse error",
        "undefined function",
        "database error",
        "error establishing a database connection",
    )
    if any(indicator in lower_html for indicator in parked_indicators):
        return False

    visible_text = soup.get_text(" ", strip=True)
    if len(visible_text) < 60:
        # Blank, dead, or parked placeholder page
        return False

    # Semantic context guard: reject personal/author/musician sites, require business signals
    excerpt = lower_html[:40_000]
    personal_hits = sum(1 for sig in _PERSONAL_SIGNALS if sig in excerpt)
    business_hits = sum(1 for sig in _BUSINESS_SIGNALS if sig in excerpt)
    if personal_hits >= 2 and business_hits == 0:
        return False
    if personal_hits >= 1 and business_hits == 0 and _looks_like_personal_name(company_name):
        return False

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
    state: str | None = None,
) -> WebsiteDiscoveryResult:
    """
    Discover and validate a likely official company website.

    The function generates a limited set of domain candidates and
    validates each candidate using the existing website fetcher.
    """

    candidates = generate_domain_candidates(
        company_name,
        state=state,
        include_legal_suffix=True,
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