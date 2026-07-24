import os
import re
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
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


SERPER_SEARCH_URL = "https://google.serper.dev/search"

DEFAULT_RESULT_COUNT = 10
DEFAULT_VALIDATION_LIMIT = 5
DEFAULT_TIMEOUT_SECONDS = 20
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


class SerperSearchError(RuntimeError):
    """
    Raised when the Serper API request fails.
    """


def _clean_company_name(company_name: str) -> str:
    """
    Remove common legal suffixes from a company name.
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
    Split 'CITY, STATE' into city and state.
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


def build_serper_queries(
    company_name: str,
    location: str | None,
) -> list[str]:
    """
    Build search queries from precise to broad.

    The resolver runs later queries only when earlier ones
    do not produce a validated official website.
    """

    normalized_name = company_name.strip()
    cleaned_name = _clean_company_name(
        normalized_name
    )

    city, state = _split_location(location)

    queries: list[str] = []

    if location:
        queries.append(
            f'"{normalized_name}" "{location}" website'
        )

    if cleaned_name and city:
        location_text = f"{city} {state}".strip()

        queries.append(
            f'"{cleaned_name}" "{location_text}"'
        )

    if cleaned_name:
        queries.append(
            f'"{cleaned_name}" official website'
        )

    unique_queries: list[str] = []

    for query in queries:
        if query not in unique_queries:
            unique_queries.append(query)

    return unique_queries


def _root_url(url: str) -> str | None:
    """
    Convert a result URL into its root website URL.
    """

    parsed_url = urlparse(url)

    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
    ):
        return None

    return (
        f"{parsed_url.scheme}://"
        f"{parsed_url.netloc}/"
    )


class SerperWebsiteResolver(WebsiteResolver):
    """
    Resolve official company websites using Serper's
    structured Google search results.

    Pipeline:
        Serper search
        -> candidate filtering
        -> scoring
        -> homepage fetching
        -> company ownership validation
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
            or os.getenv("SERPER_API_KEY", "")
        ).strip()

        if not self.api_key:
            raise ValueError(
                "SERPER_API_KEY is not configured."
            )

        if result_count < 1:
            raise ValueError(
                "Result count must be at least 1."
            )

        if validation_limit < 1:
            raise ValueError(
                "Validation limit must be at least 1."
            )

        if timeout_seconds < 1:
            raise ValueError(
                "Timeout must be at least 1 second."
            )

        self.result_count = result_count
        self.validation_limit = validation_limit
        self.timeout_seconds = timeout_seconds

    def _search(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Execute one Serper Google search.
        """

        try:
            response = requests.post(
                SERPER_SEARCH_URL,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "gl": "us",
                    "hl": "en",
                    "num": self.result_count,
                },
                timeout=self.timeout_seconds,
            )

            response.raise_for_status()

        except RequestException as exc:
            raise SerperSearchError(
                f"Serper request failed: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise SerperSearchError(
                "Serper returned invalid JSON."
            ) from exc

        organic_results = payload.get(
            "organic",
            [],
        )

        if not isinstance(organic_results, list):
            raise SerperSearchError(
                "Serper returned an unexpected format."
            )

        return [
            result
            for result in organic_results
            if isinstance(result, dict)
        ]

    def _rank_candidates(
        self,
        raw_results: list[dict[str, Any]],
        company_name: str,
        location: str | None,
        checked_candidates: list[str],
        rejected_candidates: list[str],
    ) -> list[dict[str, Any]]:
        """
        Filter, normalize, deduplicate and score results.
        """

        candidate_records: dict[
            str,
            dict[str, Any],
        ] = {}

        for raw_result in raw_results:
            title = str(
                raw_result.get("title", "")
            ).strip()

            url = str(
                raw_result.get("link", "")
            ).strip()

            description = str(
                raw_result.get("snippet", "")
            ).strip()

            if not url:
                continue

            if url not in checked_candidates:
                checked_candidates.append(url)

            filter_result = evaluate_candidate_url(
                url
            )

            if not filter_result.accepted:
                if url not in rejected_candidates:
                    rejected_candidates.append(url)

                continue

            root_url = _root_url(url)

            if root_url is None:
                continue

            score = score_search_result(
                company_name=company_name,
                location=location,
                title=title,
                url=url,
                description=description,
            )

            if score == REJECTED_SCORE:
                if url not in rejected_candidates:
                    rejected_candidates.append(url)

                continue

            candidate = {
                "score": score,
                "root_url": root_url,
                "search_url": url,
                "title": title,
                "description": description,
            }

            existing = candidate_records.get(
                root_url
            )

            if (
                existing is None
                or score > existing["score"]
            ):
                candidate_records[root_url] = (
                    candidate
                )

        return sorted(
            candidate_records.values(),
            key=lambda item: item["score"],
            reverse=True,
        )

    def _validate_candidates(
        self,
        candidates: list[dict[str, Any]],
        company_name: str,
        location: str | None,
        validated_candidates: list[str],
    ) -> tuple[str | None, list[str]]:
        """
        Fetch and validate the strongest candidates.
        """

        validation_errors: list[str] = []

        for candidate in candidates[
            :self.validation_limit
        ]:
            candidate_url = str(
                candidate["root_url"]
            )

            if candidate_url in validated_candidates:
                continue

            validated_candidates.append(
                candidate_url
            )

            fetch_result = fetch_website(
                candidate_url
            )

            if not fetch_result.success:
                validation_errors.append(
                    f"{candidate_url}: "
                    f"{fetch_result.error or 'fetch failed'}"
                )
                continue

            final_url = (
                fetch_result.final_url
                or candidate_url
            )

            html = fetch_result.html or ""

            if validate_company_homepage(
                company_name=company_name,
                location=location,
                url=final_url,
                html=html,
            ):
                return final_url, validation_errors

        return None, validation_errors

    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> WebsiteResolutionResult:
        """
        Resolve the company's most likely official website.
        """

        normalized_name = company_name.strip()

        if not normalized_name:
            return WebsiteResolutionResult(
                success=False,
                provider="serper",
                error="Company name is required.",
            )

        queries = build_serper_queries(
            company_name=normalized_name,
            location=location,
        )

        checked_candidates: list[str] = []
        rejected_candidates: list[str] = []
        validated_candidates: list[str] = []
        validation_errors: list[str] = []
        search_errors: list[str] = []

        # Run queries sequentially and stop as soon as
        # a website passes validation.
        for query in queries:
            try:
                raw_results = self._search(
                    query
                )
            except SerperSearchError as exc:
                search_errors.append(str(exc))
                continue

            ranked_candidates = (
                self._rank_candidates(
                    raw_results=raw_results,
                    company_name=normalized_name,
                    location=location,
                    checked_candidates=(
                        checked_candidates
                    ),
                    rejected_candidates=(
                        rejected_candidates
                    ),
                )
            )

            website, current_errors = (
                self._validate_candidates(
                    candidates=ranked_candidates,
                    company_name=normalized_name,
                    location=location,
                    validated_candidates=(
                        validated_candidates
                    ),
                )
            )

            validation_errors.extend(
                current_errors
            )

            if website:
                return WebsiteResolutionResult(
                    success=True,
                    website=website,
                    provider="serper",
                    query=query,
                    checked_candidates=(
                        checked_candidates
                    ),
                    rejected_candidates=(
                        rejected_candidates
                    ),
                    validated_candidates=(
                        validated_candidates
                    ),
                )

        error_parts = [
            "No Serper candidate passed homepage validation."
        ]

        if search_errors:
            error_parts.append(
                "Search errors: "
                + " | ".join(search_errors[:2])
            )

        if validation_errors:
            error_parts.append(
                "Fetch failures: "
                + " | ".join(
                    validation_errors[:3]
                )
            )

        return WebsiteResolutionResult(
            success=False,
            provider="serper",
            query=" || ".join(queries),
            checked_candidates=checked_candidates,
            rejected_candidates=rejected_candidates,
            validated_candidates=validated_candidates,
            error=" ".join(error_parts),
        )