import re
from typing import Optional

import requests
from requests import Response
from requests.exceptions import RequestException

from automation.models.fetch_result import FetchResult


DEFAULT_TIMEOUT = 15

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
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
    - returns the final resolved URL.
    """

    normalized_url = normalize_url(url)

    if normalized_url is None:
        return FetchResult(
            success=False,
            error="A valid website URL was not provided.",
        )

    try:
        response = requests.get(
            normalized_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )

        response.raise_for_status()

        if not _is_html_response(response):
            return FetchResult(
                success=False,
                final_url=response.url,
                status_code=response.status_code,
                error="The requested URL did not return an HTML page.",
            )

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