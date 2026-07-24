from urllib.parse import urlparse, urlunparse


DOMAIN_MAP = {
    "m.facebook.com": "facebook.com",
    "mobile.twitter.com": "twitter.com",
}


def normalize_domain(host: str) -> str:
    """
    Convert localized or mobile domains to a canonical hostname.
    """

    host = host.lower().strip()

    # Handle all LinkedIn country domains
    if host.endswith(".linkedin.com") and host != "linkedin.com":
        return "linkedin.com"

    return DOMAIN_MAP.get(host, host)


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison and deduplication.
    """

    parsed = urlparse(url)

    host = normalize_domain(parsed.netloc)

    path = parsed.path.rstrip("/")

    return urlunparse(
        (
            parsed.scheme.lower(),
            host,
            path,
            "",
            "",
            "",
        )
    )


def domain(url: str) -> str:
    """
    Return the normalized hostname.
    """

    return normalize_domain(
        urlparse(url).netloc
    )


def deduplicate_urls(
    urls: list[str],
) -> list[str]:
    """
    Remove duplicate URLs after normalization.
    """

    seen = set()
    output = []

    for url in urls:

        normalized = normalize_url(url)

        if normalized in seen:
            continue

        seen.add(normalized)
        output.append(url)

    return output