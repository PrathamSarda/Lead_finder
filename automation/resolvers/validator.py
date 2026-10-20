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

# Generic industry / service category terms that must not alone constitute brand identity
GENERIC_INDUSTRY_WORDS = {
    "and", "group", "international", "industries", "industry", "services",
    "service", "solutions", "enterprises", "enterprise", "holdings",
    "delivery", "transfer", "transport", "transportation", "trucking",
    "freight", "logistics", "shipping", "storage", "moving",
    "supplies", "products", "materials", "sales", "contracting",
    "construction", "commercial", "industrial", "management",
}

# Keywords that strongly indicate a personal/author/blog site rather than a business
PERSONAL_SITE_SIGNALS = {
    "author", "novelist", "fiction", "nonfiction", "non-fiction",
    "mystery", "thriller", "romance", "biography", "memoir",
    "espionage", "spy novel", "bestseller", "book series",
    "blog", "my blog", "personal website", "personal site",
    "freelance writer", "freelance journalist", "poet", "poetry",
    "screenplay", "screenwriter", "illustrator", "artist portfolio",
    "photographer", "photography portfolio",
    "musician", "jazz", "trio", "pianist", "guitarist", "recording artist",
    "discography", "live concerts", "tour dates", "album release", "stream music",
    "movies", "film", "filmmaker", "actor", "actress", "director", "cinema",
    "theatre", "theater", "acting", "casting", "screenplay",
}

ERROR_PAGE_SIGNALS = {
    "not acceptable!", "406 not acceptable", "mod_security",
    "access denied", "403 forbidden", "404 not found",
    "page not found", "blocked by cloudflare", "attention required! | cloudflare",
    "security check to access", "just a moment...", "ray id:",
    "error 404", "error 403", "error 500", "502 bad gateway",
    "503 service unavailable", "504 gateway time-out",
}

# Keywords that indicate a legitimate US business website
BUSINESS_SITE_SIGNALS = {
    # Freight / trucking / transport
    "freight", "trucking", "carrier", "transport", "logistics",
    "shipping", "delivery", "dispatch", "fleet", "trailer",
    "fmcsa", "dot number", "motor carrier", "truck",
    # Chemicals / manufacturing
    "bleach", "chemical", "manufacturing", "industrial",
    "distributor", "wholesale", "product", "production",
    # General commerce
    "our services", "contact us", "request a quote", "get a quote",
    "about us", "our team", "our company", "our clients",
    "careers", "employment", "hire us",
    "equipment", "contractor", "construction",
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


def _looks_like_personal_name(company_name: str) -> bool:
    """
    Return True when the company name looks like a personal first-last name.

    Heuristic: exactly two meaningful tokens, both purely alphabetic,
    each 2-15 characters long, with no legal suffixes or generic words.
    e.g. 'Glen Dyer', 'Richard Austin', 'James Austin'
    """
    tokens = re.findall(r"[a-z]+", company_name.lower())
    meaningful = [
        t for t in tokens
        if t not in LEGAL_SUFFIXES and t not in GENERIC_WORDS
        and t not in GENERIC_INDUSTRY_WORDS and len(t) >= 2
    ]
    return len(meaningful) == 2 and all(2 <= len(t) <= 15 for t in meaningful)


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

    Additional semantic guard: personal author/blog sites are rejected
    even when the domain and page contain the company name tokens,
    because the company may share its name with a private individual.
    """

    if not html.strip():
        return False

    lower_html = html.lower()
    if any(sig in lower_html[:4000] for sig in ERROR_PAGE_SIGNALS):
        return False

    parked_indicators = (
        "/lander",
        "buy this domain",
        "domain is for sale",
        "this domain may be for sale",
        "inquire about this domain",
        "domain has expired",
        "hugedomains.com",
        "dan.com",
        "sedoparking.com",
        "afternic.com",
        "parked domain",
        "godaddy parked",
        "fatal error",
        "parse error",
        "undefined function",
        "database error",
        "error establishing a database connection",
    )
    if any(indicator in lower_html for indicator in parked_indicators):
        return False

    # --- Semantic context guard ---
    # Reject personal author / blog / portfolio sites masquerading as businesses.
    # We check a broader excerpt of the page (up to 40 000 chars) for personal signals.
    personal_signals_found = sum(
        1 for sig in PERSONAL_SITE_SIGNALS if sig in lower_html[:40_000]
    )
    business_signals_found = sum(
        1 for sig in BUSINESS_SITE_SIGNALS if sig in lower_html[:40_000]
    )
    # If the page shows personal/author/entertainer indicators, reject it immediately.
    if personal_signals_found >= 2:
        return False
    # Any personal signal on a personal-name company (e.g. Gary Anderson, Glen Dyer) is an immediate reject
    if personal_signals_found >= 1 and _looks_like_personal_name(company_name):
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

    if len(page_text) < 20:
        return False

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

    # Initialism matching: check if hostname starts with the company's initials
    # e.g. hostname "aicpittsburgh" matches "American Industrial Contracting Inc" via "aic"
    INITIALISM_MIN_TOKENS = 2
    initialism_meaningful = [
        t for t in re.findall(r"[a-z0-9]+", company_name.lower())
        if t not in LEGAL_SUFFIXES and len(t) >= 2
    ]
    company_initials = "".join(t[0] for t in initialism_meaningful)
    if (
        len(company_initials) >= INITIALISM_MIN_TOKENS
        and len(hostname_matches) == 0
        and hostname_text.startswith(company_initials)
    ):
        # Treat initialism match as a synthetic hostname match for all tokens
        # (company name must still appear in title/headings for full verification)
        hostname_matches = {company_tokens[0]} if company_tokens else set()

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

    parsed_candidate = urlparse(url)
    candidate_host = parsed_candidate.netloc.lower()
    candidate_tld = candidate_host.split(".")[-1]
    foreign_cctlds = {
        "jo", "ru", "cn", "in", "pk", "ir", "by", "vn", "br", "ng", "za", "tr", "ua", "kz", "sa", "eg"
    }
    if candidate_tld in foreign_cctlds:
        return False

    if len(company_tokens) == 1:
        token = company_tokens[0]
        has_ownership_signal = (
            token in hostname_text
            or token in normalized_title
            or token in normalized_headings
        )
        if not has_ownership_signal:
            return False

        name_without_suffix = [
            t
            for t in re.findall(r"[a-z0-9]+", company_name.lower())
            if t not in LEGAL_SUFFIXES and len(t) >= 2
        ]
        if token in hostname_text and name_without_suffix and all(
            t in normalized_title or t in normalized_headings
            for t in name_without_suffix
        ):
            return True

        raw_company_tokens = re.findall(r"[a-z0-9]+", company_name.lower())
        exact_host_match = all(t in hostname_text for t in raw_company_tokens)
        if exact_host_match:
            return True

        location_text = _normalize_text(location)
        if location_text:
            location_tokens = [t for t in location_text.split() if len(t) >= 2]
            loc_in_page = any(lt in normalized_page_text for lt in location_tokens)
            if loc_in_page:
                return True
            return False

        # Personal name companies: require location context even without explicit location arg
        if _looks_like_personal_name(company_name):
            # Without location context we cannot distinguish Glen Dyer (trucker) from
            # Glen Dyer (author). Reject to avoid false positives.
            return False

        return True

    # Guard against generic industry word collisions (e.g. Compton Transfer matching Boise Delivery & Transfer via 'delivery' + 'transfer')
    distinctive_tokens = [
        t for t in company_tokens if t not in GENERIC_INDUSTRY_WORDS
    ]
    if distinctive_tokens and not any(t in strong_matches for t in distinctive_tokens):
        # Company has distinctive name tokens, but strong matches only contain generic industry terms.
        # Reject to prevent matching competitors or unrelated companies in the same industry.
        return False

    # Guard for personal-name companies (e.g. James Austin, Glen Dyer, Richard Austin):
    # Having name tokens in a domain or title is not enough without location corroboration
    # or clear business context.
    if _looks_like_personal_name(company_name):
        if personal_signals_found >= 1:
            return False

        location_corroborated = False
        if location:
            parts = [p.strip().lower() for p in location.split(",") if p.strip()]
            city_part = parts[0] if parts else ""
            state_part = parts[1].strip() if len(parts) > 1 else ""
            if city_part and len(city_part) >= 3 and city_part in normalized_page_text:
                location_corroborated = True
            elif state_part and (
                state_part in normalized_page_text.split()
                or (len(state_part) == 2 and re.search(rf"\b{re.escape(state_part)}\b", normalized_page_text))
            ):
                location_corroborated = True

        has_biz_signal = business_signals_found >= 1 and personal_signals_found == 0
        if not location_corroborated and not has_biz_signal:
            return False

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
            (len(strong_matches) >= 2 or (len(strong_matches) >= 1 and len(page_matches) >= len(company_tokens)))
            and len(page_matches) >= 2
            and location_matches >= 1
        ):
            return True

    return False