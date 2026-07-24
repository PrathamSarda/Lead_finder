from __future__ import annotations
from automation.resolvers.query_builder import (
    build_search_queries,
)
from automation.resolvers.domain_similarity import (
    calculate_domain_bonus,
)

import os
import re
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from requests import Response
from requests.exceptions import RequestException

from automation.enrichment.website_fetcher import fetch_website
from automation.models.website_resolution_result import (
    WebsiteResolutionResult,
)
from automation.resolvers.base import WebsiteResolver
from automation.resolvers.candidate_filter import (
    evaluate_candidate_url,
)
from automation.resolvers.scorer import score_search_result
from automation.resolvers.validator import (
    validate_company_homepage,
)


ZENSERP_SEARCH_URL = "https://app.zenserp.com/api/v2/search"

DEFAULT_RESULT_COUNT = 10
DEFAULT_VALIDATION_LIMIT = 5
DEFAULT_TIMEOUT_SECONDS = 30

REJECTED_SCORE = -1_000


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


class ZenserpSearchError(RuntimeError):
    """Raised when a Zenserp API request fails."""


def _clean_company_name(company_name: str) -> str:
    """
    Remove common legal suffixes from a company name.

    Example:
        "CHEROKEE CULVERT COMPANY INC"
        -> "cherokee culvert"
    """

    tokens = re.findall(
        r"[a-z0-9]+",
        company_name.lower(),
    )

    cleaned_tokens = [
        token
        for token in tokens
        if token not in LEGAL_SUFFIXES
    ]

    return " ".join(cleaned_tokens).strip()


def _split_location(
    location: str | None,
) -> tuple[str, str]:
    """
    Split a location such as 'MACON, GA' into city and state.
    """

    if not location:
        return "", ""

    parts = [
        part.strip()
        for part in location.split(",")
        if part.strip()
    ]

    city = parts[0] if parts else ""
    state = parts[1] if len(parts) > 1 else ""

    return city, state




def _root_url(url: str) -> str | None:
    """
    Convert a search-result URL into its root website URL.

    Example:
        https://example.com/about/team
        -> https://example.com/
    """

    try:
        parsed_url = urlparse(url)
    except ValueError:
        return None

    if parsed_url.scheme not in {"http", "https"}:
        return None

    if not parsed_url.netloc:
        return None

    return f"{parsed_url.scheme}://{parsed_url.netloc}/"


def _response_error_message(response: Response) -> str:
    """
    Build a safe diagnostic message from a failed response.
    """

    body_preview = response.text.strip()[:500]

    if not body_preview:
        body_preview = "No response body returned."

    return (
        f"Zenserp request failed with HTTP "
        f"{response.status_code}: {body_preview}"
    )


class ZenserpWebsiteResolver(WebsiteResolver):
    """
    Resolve official company websites using Zenserp.

    Processing flow:

        Zenserp Google search
        -> candidate URL filtering
        -> candidate scoring
        -> homepage fetching
        -> company homepage validation
    """

    def __init__(
        self,
        api_key: str | None = None,
        result_count: int = DEFAULT_RESULT_COUNT,
        validation_limit: int = DEFAULT_VALIDATION_LIMIT,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        load_dotenv()

        self.api_key = (
            api_key
            or os.getenv("ZENSERP_API_KEY", "")
        ).strip()

        if not self.api_key:
            raise ValueError(
                "ZENSERP_API_KEY is not configured. "
                "Add it to the project-root .env file."
            )

        if result_count < 1:
            raise ValueError(
                "result_count must be at least 1."
            )

        if validation_limit < 1:
            raise ValueError(
                "validation_limit must be at least 1."
            )

        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be at least 1."
            )

        self.result_count = result_count
        self.validation_limit = validation_limit
        self.timeout_seconds = timeout_seconds

    def _search(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Execute one Zenserp Google search request.
        """

        try:
            response = requests.get(
                ZENSERP_SEARCH_URL,
                headers={
                    "apikey": self.api_key,
                    "Accept": "application/json",
                },
                params={
                    "q": query,
                    "engine": "google",
                    "gl": "us",
                    "hl": "en",
                    "num": self.result_count,
                },
                timeout=self.timeout_seconds,
            )

        except RequestException as exc:
            raise ZenserpSearchError(
                f"Zenserp network request failed: {exc}"
            ) from exc

        if not response.ok:
            raise ZenserpSearchError(
                _response_error_message(response)
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ZenserpSearchError(
                "Zenserp returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise ZenserpSearchError(
                "Zenserp returned an unexpected response type."
            )

        organic_results = payload.get("organic", [])

        if organic_results is None:
            return []

        if not isinstance(organic_results, list):
            raise ZenserpSearchError(
                "Zenserp returned an unexpected organic-results format."
            )

        return [
            result
            for result in organic_results
            if isinstance(result, dict)
        ]

    

    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> WebsiteResolutionResult:
        """
        Resolve the official website for one company.
        """

        normalized_name = company_name.strip()

        if not normalized_name:
            return WebsiteResolutionResult(
                success=False,
                provider="zenserp",
                error="Company name is required.",
            )

        queries = build_search_queries(
        company_name=normalized_name,
        location=location,
        )
        last_error = None

        checked_candidates: list[str] = []
        rejected_candidates: list[str] = []
        validated_candidates: list[str] = []

        for query in queries:

            try:
                raw_results = self._search(query)

            except ZenserpSearchError as exc:
                last_error = str(exc)
                continue

            if not raw_results:
                continue

            ranked_candidates = self._rank_candidates(
                raw_results=raw_results,
                company_name=normalized_name,
                location=location,
                checked_candidates=checked_candidates,
                rejected_candidates=rejected_candidates,
            )

            if not ranked_candidates:
                continue

            website, validation_errors = self._validate_candidates(
                candidates=ranked_candidates,
                company_name=normalized_name,
                location=location,
                validated_candidates=validated_candidates,
            )

            if website:

                return WebsiteResolutionResult(
                    success=True,
                    website=website,
                    provider="zenserp",
                    query=query,
                    checked_candidates=checked_candidates,
                    rejected_candidates=rejected_candidates,
                    validated_candidates=validated_candidates,
                )

            if validation_errors:
                last_error = " | ".join(validation_errors)

                if website:
                    return WebsiteResolutionResult(
                        success=True,
                        website=website,
                        provider="zenserp",
                        query=query,
                        checked_candidates=checked_candidates,
                        rejected_candidates=rejected_candidates,
                        validated_candidates=validated_candidates,
                    )

                error_message = (
                    "No Zenserp candidate passed homepage validation."
                )

                if validation_errors:
                    error_message += (
                        " Fetch errors: "
                        + " | ".join(validation_errors[:3])
                    )

                return WebsiteResolutionResult(
            success=False,
            provider="zenserp",
            query=queries[-1],
            checked_candidates=checked_candidates,
            rejected_candidates=rejected_candidates,
            validated_candidates=validated_candidates,
            error=last_error or "Official website not found.",
            )