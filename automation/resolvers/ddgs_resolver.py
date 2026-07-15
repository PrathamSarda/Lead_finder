import re
import time
from automation.resolvers.candidate_filter import (
    evaluate_candidate_url,
)
from urllib.parse import urlparse

from ddgs import DDGS

from automation.enrichment.website_fetcher import fetch_website
from automation.models.website_resolution_result import (
    WebsiteResolutionResult,
)
from automation.resolvers.base import WebsiteResolver
from automation.resolvers.scorer import score_search_result
from automation.resolvers.validator import (
    validate_company_homepage,
)


DEFAULT_RESULT_COUNT = 10
DEFAULT_VALIDATION_LIMIT = 6
DEFAULT_QUERY_DELAY_SECONDS = 1.5
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


def _clean_company_name(company_name: str) -> str:
    """
    Remove common legal suffixes from a company name.

    Example:
        "Prairie Sand & Gravel Inc"
        becomes
        "Prairie Sand Gravel"
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
    Split a location such as 'FAYETTEVILLE, AR'
    into city and state.
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


def build_search_queries(
    company_name: str,
    location: str | None,
) -> list[str]:
    """
    Build multiple search queries with different levels
    of strictness.

    Queries are ordered from most precise to broadest.
    """

    normalized_company_name = company_name.strip()
    cleaned_company_name = _clean_company_name(
        normalized_company_name
    )

    city, state = _split_location(location)

    queries: list[str] = []

    if location:
        queries.append(
            f'"{normalized_company_name}" '
            f'"{location}" website'
        )

    if cleaned_company_name and city:
        location_part = f"{city} {state}".strip()

        queries.append(
            f'"{cleaned_company_name}" '
            f'"{location_part}"'
        )

    if cleaned_company_name:
        queries.append(
            f'"{cleaned_company_name}" website'
        )

    queries.append(
        f'"{normalized_company_name}"'
    )

    unique_queries: list[str] = []

    for query in queries:
        if query not in unique_queries:
            unique_queries.append(query)

    return unique_queries


def _root_url(url: str) -> str | None:
    """
    Convert a search-result URL into its root website URL.
    """

    parsed_url = urlparse(url)

    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
    ):
        return None

    return f"{parsed_url.scheme}://{parsed_url.netloc}/"


class DDGSWebsiteResolver(WebsiteResolver):
    """
    Experimental website resolver using multiple DDGS queries,
    candidate scoring, and homepage validation.
    """

    def __init__(
        self,
        max_results: int = DEFAULT_RESULT_COUNT,
        validation_limit: int = DEFAULT_VALIDATION_LIMIT,
        query_delay_seconds: float = (
            DEFAULT_QUERY_DELAY_SECONDS
        ),
    ) -> None:
        if max_results < 1:
            raise ValueError(
                "Resolver result count must be at least 1."
            )

        if validation_limit < 1:
            raise ValueError(
                "Validation limit must be at least 1."
            )

        if query_delay_seconds < 0:
            raise ValueError(
                "Query delay cannot be negative."
            )

        self.max_results = max_results
        self.validation_limit = validation_limit
        self.query_delay_seconds = (
            query_delay_seconds
        )

    def _search_query(
        self,
        query: str,
    ) -> list[dict]:
        """
        Execute one DDGS query.

        Search failures are treated as empty results so another
        query strategy can still be attempted.
        """

        try:
            return list(
                DDGS().text(
                    query=query,
                    region="us-en",
                    safesearch="moderate",
                    max_results=self.max_results,
                    backend="auto",
                )
            )
        except Exception:
            return []

    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> WebsiteResolutionResult:
        """
        Resolve the most likely official company website.
        """

        normalized_company_name = company_name.strip()

        if not normalized_company_name:
            return WebsiteResolutionResult(
                success=False,
                provider="ddgs",
                error="Company name is required.",
            )

        queries = build_search_queries(
            company_name=normalized_company_name,
            location=location,
        )

        checked_candidates: list[str] = []
        rejected_candidates: list[str] = []
        validated_candidates: list[str] = []

        candidate_records: dict[str, dict] = {}

        for query_index, query in enumerate(queries):
            raw_results = self._search_query(query)

            for raw_result in raw_results:
                if not isinstance(raw_result, dict):
                    continue

                title = str(
                    raw_result.get("title", "")
                ).strip()

                url = str(
                    raw_result.get("href", "")
                ).strip()

                description = str(
                    raw_result.get("body", "")
                ).strip()

                if not url:
                    continue

                if url not in checked_candidates:
                    checked_candidates.append(url)

                filter_result = evaluate_candidate_url(
                url
                )

                if not filter_result.accepted:
                    rejected_candidates.append(url)
                    continue

                root_url = _root_url(url)

                if root_url is None:
                    continue

                score = score_search_result(
                    company_name=normalized_company_name,
                    location=location,
                    title=title,
                    url=url,
                    description=description,
                )

                if score == REJECTED_SCORE:
                    continue

                existing = candidate_records.get(root_url)

                candidate = {
                    "score": score,
                    "url": root_url,
                    "title": title,
                    "description": description,
                }

                if (
                    existing is None
                    or score > existing["score"]
                ):
                    candidate_records[root_url] = (
                        candidate
                    )

            if (
                query_index < len(queries) - 1
                and self.query_delay_seconds
            ):
                time.sleep(
                    self.query_delay_seconds
                )

        ranked_candidates = sorted(
            candidate_records.values(),
            key=lambda candidate: candidate["score"],
            reverse=True,
        )

        candidates_to_validate = ranked_candidates[
            :self.validation_limit
        ]

        validation_errors: list[str] = []

        for candidate in candidates_to_validate:
            candidate_url = candidate["url"]

            fetch_result = fetch_website(
                candidate_url
            )
            
            validated_candidates.append(
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

            is_valid = validate_company_homepage(
                company_name=normalized_company_name,
                location=location,
                url=final_url,
                html=html,
            )

            if is_valid:
                return WebsiteResolutionResult(
                success=True,
                website=final_url,
                provider="ddgs",
                query=" || ".join(queries),
                checked_candidates=checked_candidates,
                rejected_candidates=rejected_candidates,
                validated_candidates=validated_candidates,
            )

        error_parts = [
            "No search candidate passed homepage validation."
        ]

        if not candidate_records:
            error_parts.append(
                "No non-directory candidates were found."
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
        provider="ddgs",
        query=" || ".join(queries),
        checked_candidates=checked_candidates,
        rejected_candidates=rejected_candidates,
        validated_candidates=validated_candidates,
        error=" ".join(error_parts),
    )