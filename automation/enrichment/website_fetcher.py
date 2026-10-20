import re
from typing import Optional

import requests
from requests import Response
from requests.exceptions import RequestException

from automation.models.fetch_result import FetchResult


DEFAULT_TIMEOUT = 5

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

FALLBACK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize a website URL before sending the HTTP request.

    Returns None when the supplied value is empty or invalid.
    """

    if not isinstance(url, str):
        return None

    normalized_url = url.strip()

    if not normalized_url:
        return None

    if not re.match(r"^https?://", normalized_url, flags=re.IGNORECASE):
        normalized_url = f"https://{normalized_url}"

    return normalized_url


def _is_html_response(response: Response) -> bool:
    """
    Check whether the response appears to contain HTML.
    """

    content_type = response.headers.get("Content-Type", "").lower()

    return (
        "text/html" in content_type
        or "application/xhtml+xml" in content_type
    )


def fetch_website(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> FetchResult:
    """
    Download a website and return a structured fetch result.

    The function:
    - normalizes missing URL schemes,
    - follows redirects,
    - validates the response type,
    - catches request errors,
    - gracefully retries with fallback headers and SSL bypass if initial attempt fails.
    """

    normalized_url = normalize_url(url)

    if normalized_url is None:
        return FetchResult(
            success=False,
            error="A valid website URL was not provided.",
        )

    # Attempt 1: Normal request
    try:
        response = requests.get(
            normalized_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        if _is_html_response(response) or len(response.text) > 200:
            return FetchResult(
                success=True,
                final_url=response.url,
                html=response.text,
                status_code=response.status_code,
            )

    except RequestException:
        pass

    # Attempt 2: Fallback with verify=False and minimal headers
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            normalized_url,
            headers=FALLBACK_HEADERS,
            timeout=timeout,
            allow_redirects=True,
            verify=False,
        )
        response.raise_for_status()

        return FetchResult(
            success=True,
            final_url=response.url,
            html=response.text,
            status_code=response.status_code,
        )
    except RequestException as exc:
        status_code = None
        final_url = normalized_url
        if exc.response is not None:
            status_code = exc.response.status_code
            final_url = exc.response.url

        return FetchResult(
            success=False,
            final_url=final_url,
            status_code=status_code,
            error=str(exc),
        )