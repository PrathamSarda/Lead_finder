from __future__ import annotations

import logging
from collections.abc import Iterable
from urllib.parse import urlparse, urlunparse

import requests

from automation.resolvers.candidate_filter import (
    evaluate_candidate_url,
)
from automation.resolvers.domain_similarity import (
    calculate_domain_bonus,
)
from automation.resolvers.models import (
    RankedCandidate,
    ResolutionResult,
)
from automation.resolvers.providers.base import (
    SearchProvider,
    SearchProviderError,
    SearchResult,
)
from automation.resolvers.providers.ddgs_resolver import DDGSProvider
from automation.resolvers.zenserp_resolver import (
    ZenserpProvider,
)
from automation.resolvers.query_builder import (
    build_search_queries,
)
from automation.resolvers.scorer import (
    MIN_ACCEPTABLE_SCORE,
    score_search_result,
)
from automation.resolvers.validator import (
    validate_company_homepage,
)


logger = logging.getLogger(__name__)


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class WebsiteResolver:
    """
    Resolve the most likely official company website.

    Resolution pipeline:

        query generation
            ↓
        search provider
            ↓
        URL filtering
            ↓
        candidate scoring
            ↓
        domain similarity bonus
            ↓
        homepage fetching
            ↓
        company homepage validation

    Providers are processed sequentially. Therefore, the second provider
    behaves as a fallback when the first provider cannot produce a
    validated result.
    """

    def __init__(
        self,
        providers: list[SearchProvider] | None = None,
        acceptance_threshold: int = 90,
        request_timeout: float = 12.0,
        max_validation_candidates: int = 8,
        max_results_per_provider: int = 40,
        session: requests.Session | None = None,
    ) -> None:
        """
        Initialize the resolver.

        Args:
            providers:
                Ordered list of search providers. The first provider is
                attempted first; later providers act as fallbacks.

            acceptance_threshold:
                Preferred minimum combined score for a candidate.

                Candidates below this value may still be validated when
                no higher-scoring candidates exist, provided they meet
                MIN_ACCEPTABLE_SCORE.

            request_timeout:
                Timeout in seconds for homepage requests.

            max_validation_candidates:
                Maximum number of candidates whose websites will be
                downloaded and validated per provider.

            max_results_per_provider:
                Maximum number of unique raw results retained from each
                provider.

            session:
                Optional requests.Session, useful for dependency injection
                and testing.
        """

        if acceptance_threshold < 0:
            raise ValueError(
                "acceptance_threshold cannot be negative."
            )

        if request_timeout <= 0:
            raise ValueError(
                "request_timeout must be greater than zero."
            )

        if max_validation_candidates <= 0:
            raise ValueError(
                "max_validation_candidates must be greater than zero."
            )

        if max_results_per_provider <= 0:
            raise ValueError(
                "max_results_per_provider must be greater than zero."
            )

        self.providers = (
            providers
            if providers is not None
            else [
                ZenserpProvider(),
                DDGSProvider(),
            ]
        )

        self.acceptance_threshold = acceptance_threshold
        self.request_timeout = request_timeout
        self.max_validation_candidates = (
            max_validation_candidates
        )
        self.max_results_per_provider = (
            max_results_per_provider
        )

        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "image/avif,"
                    "image/webp,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> ResolutionResult:
        """
        Resolve the official website for a company.

        Providers are attempted in their configured order. If the first
        provider cannot produce a validated website, the resolver moves
        to the next provider.

        Args:
            company_name:
                Legal or commonly used company name.

            location:
                Optional city/state or other location context.

        Returns:
            ResolutionResult describing whether a website was found.
        """

        normalized_company_name = company_name.strip()

        if not normalized_company_name:
            raise ValueError(
                "company_name cannot be empty."
            )

        normalized_location = (
            location.strip()
            if location and location.strip()
            else None
        )

        if not self.providers:
            return ResolutionResult(
                found=False,
                reason="no_search_providers_configured",
            )

        total_attempted_candidates = 0
        provider_failures: list[str] = []

        for provider in self.providers:
            provider_name = self._provider_name(provider)

            logger.info(
                "Resolving website for %s using provider %s",
                normalized_company_name,
                provider_name,
            )

            try:
                search_results = self._search_provider(
                    provider=provider,
                    company_name=normalized_company_name,
                    location=normalized_location,
                )
            except SearchProviderError as exc:
                logger.warning(
                    "Search provider %s failed for %s: %s",
                    provider_name,
                    normalized_company_name,
                    exc,
                )

                provider_failures.append(provider_name)
                continue

            except Exception as exc:
                logger.exception(
                    "Unexpected error from provider %s while "
                    "resolving %s",
                    provider_name,
                    normalized_company_name,
                )

                provider_failures.append(provider_name)
                continue

            if not search_results:
                logger.info(
                    "Provider %s returned no search results for %s",
                    provider_name,
                    normalized_company_name,
                )
                continue

            ranked_candidates = self._rank_candidates(
                company_name=normalized_company_name,
                location=normalized_location,
                search_results=search_results,
            )

            if not ranked_candidates:
                logger.info(
                    "Provider %s returned no acceptable candidates "
                    "for %s",
                    provider_name,
                    normalized_company_name,
                )
                continue

            validation_result = self._validate_candidates(
                company_name=normalized_company_name,
                location=normalized_location,
                candidates=ranked_candidates,
            )

            total_attempted_candidates += (
                validation_result.attempted_candidates
            )

            if validation_result.found:
                logger.info(
                    "Resolved %s to %s using %s with score %s",
                    normalized_company_name,
                    validation_result.website,
                    validation_result.provider,
                    validation_result.score,
                )

                return ResolutionResult(
                    found=True,
                    website=validation_result.website,
                    provider=validation_result.provider,
                    score=validation_result.score,
                    validated=True,
                    search_result=(
                        validation_result.search_result
                    ),
                    reason=None,
                    attempted_candidates=(
                        total_attempted_candidates
                    ),
                )

        if provider_failures and (
            len(provider_failures) == len(self.providers)
        ):
            reason = "all_search_providers_failed"
        else:
            reason = "no_validated_website_found"

        return ResolutionResult(
            found=False,
            reason=reason,
            attempted_candidates=total_attempted_candidates,
        )

    def search_all(
        self,
        company_name: str,
        location: str | None = None,
    ) -> list[SearchResult]:
        """
        Return deduplicated raw results from all configured providers.

        This method is intended primarily for debugging and benchmark
        inspection. Production code should normally call resolve().
        """

        normalized_company_name = company_name.strip()

        if not normalized_company_name:
            raise ValueError(
                "company_name cannot be empty."
            )

        normalized_location = (
            location.strip()
            if location and location.strip()
            else None
        )

        collected_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for provider in self.providers:
            try:
                provider_results = self._search_provider(
                    provider=provider,
                    company_name=normalized_company_name,
                    location=normalized_location,
                )
            except Exception:
                logger.exception(
                    "Provider %s failed during search_all()",
                    self._provider_name(provider),
                )
                continue

            for result in provider_results:
                normalized_url = self._normalize_result_url(
                    result.url
                )

                if not normalized_url:
                    continue

                identity = normalized_url.lower()

                if identity in seen_urls:
                    continue

                seen_urls.add(identity)
                collected_results.append(result)

        return collected_results

    def _search_provider(
        self,
        provider: SearchProvider,
        company_name: str,
        location: str | None,
    ) -> list[SearchResult]:
        """
        Execute generated queries against one provider.

        Results are deduplicated by normalized URL.
        """

        queries = build_search_queries(
            company_name,
            location,
        )

        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in queries:
            if len(results) >= self.max_results_per_provider:
                break

            logger.debug(
                "Searching provider %s with query: %s",
                self._provider_name(provider),
                query,
            )

            try:
                query_results = provider.search(query)
            except SearchProviderError:
                raise
            except Exception as exc:
                raise SearchProviderError(
                    f"{self._provider_name(provider)} search failed "
                    f"for query {query!r}: {exc}"
                ) from exc

            for result in query_results:
                if len(results) >= self.max_results_per_provider:
                    break

                normalized_url = self._normalize_result_url(
                    result.url
                )

                if not normalized_url:
                    continue

                identity = normalized_url.lower()

                if identity in seen_urls:
                    continue

                seen_urls.add(identity)
                results.append(result)

        return results

    def _rank_candidates(
        self,
        company_name: str,
        location: str | None,
        search_results: Iterable[SearchResult],
    ) -> list[RankedCandidate]:
        """
        Filter, score, and rank raw search results.
        """

        candidates: list[RankedCandidate] = []
        seen_homepages: set[str] = set()

        for result in search_results:
            normalized_url = self._normalize_result_url(
                result.url
            )

            if not normalized_url:
                continue

            homepage_url = self._to_homepage_url(
                normalized_url
            )

            if not homepage_url:
                continue

            homepage_identity = homepage_url.lower()

            if homepage_identity in seen_homepages:
                continue

            filter_result = evaluate_candidate_url(
                homepage_url
            )

            if not filter_result.accepted:
                logger.debug(
                    "Rejected candidate %s: %s",
                    result.url,
                    filter_result.reason,
                )
                continue

            search_score = score_search_result(
                company_name=company_name,
                location=location,
                title=result.title,
                url=homepage_url,
                description=result.snippet,
            )

            if search_score < MIN_ACCEPTABLE_SCORE:
                logger.debug(
                    "Rejected low-scoring candidate %s: %s",
                    homepage_url,
                    search_score,
                )
                continue

            domain_bonus = calculate_domain_bonus(
                company_name=company_name,
                url=homepage_url,
            )

            total_score = search_score + domain_bonus

            seen_homepages.add(homepage_identity)

            candidates.append(
                RankedCandidate(
                    search_result=result,
                    normalized_url=homepage_url,
                    search_score=search_score,
                    domain_bonus=domain_bonus,
                    total_score=total_score,
                )
            )

        candidates.sort(
            key=self._candidate_sort_key,
            reverse=True,
        )

        return candidates

    def _validate_candidates(
        self,
        company_name: str,
        location: str | None,
        candidates: list[RankedCandidate],
    ) -> ResolutionResult:
        """
        Fetch and validate the highest-ranked candidates.

        High-confidence candidates are validated first. If none meet the
        preferred acceptance threshold, the best remaining candidates
        are still tested because homepage validation is the final gate.
        """

        candidates_to_validate = self._select_validation_candidates(
            candidates
        )

        attempted_candidates = 0

        for candidate in candidates_to_validate:
            attempted_candidates += 1

            logger.debug(
                "Validating candidate %s with total score %s",
                candidate.normalized_url,
                candidate.total_score,
            )

            fetched_page = self._fetch_homepage(
                candidate.normalized_url
            )

            if fetched_page is None:
                continue

            final_url, html = fetched_page

            filter_result = evaluate_candidate_url(
                final_url
            )

            if not filter_result.accepted:
                logger.debug(
                    "Candidate redirected to rejected URL %s: %s",
                    final_url,
                    filter_result.reason,
                )
                continue

            is_valid = validate_company_homepage(
                company_name=company_name,
                location=location,
                url=final_url,
                html=html,
            )

            if not is_valid:
                logger.debug(
                    "Homepage validation failed for %s",
                    final_url,
                )
                continue

            resolved_url = self._to_homepage_url(
                final_url
            )

            return ResolutionResult(
                found=True,
                website=resolved_url,
                provider=(
                    candidate.search_result.provider
                ),
                score=candidate.total_score,
                validated=True,
                search_result=candidate.search_result,
                reason=None,
                attempted_candidates=attempted_candidates,
            )

        return ResolutionResult(
            found=False,
            reason="provider_candidates_failed_validation",
            attempted_candidates=attempted_candidates,
        )

    def _select_validation_candidates(
        self,
        candidates: list[RankedCandidate],
    ) -> list[RankedCandidate]:
        """
        Select candidates for network validation.

        Candidates meeting acceptance_threshold are tried first. Lower
        ranked candidates are appended afterward as a controlled fallback.
        """

        preferred_candidates = [
            candidate
            for candidate in candidates
            if candidate.total_score
            >= self.acceptance_threshold
        ]

        fallback_candidates = [
            candidate
            for candidate in candidates
            if candidate.total_score
            < self.acceptance_threshold
        ]

        ordered_candidates = (
            preferred_candidates
            + fallback_candidates
        )

        return ordered_candidates[
            : self.max_validation_candidates
        ]

    def _fetch_homepage(
        self,
        url: str,
    ) -> tuple[str, str] | None:
        """
        Download a candidate homepage.

        Returns:
            Tuple containing the final response URL and HTML, or None
            when the page cannot safely be fetched.
        """

        try:
            response = self.session.get(
                url,
                timeout=self.request_timeout,
                allow_redirects=True,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            logger.debug(
                "Failed to fetch %s: %s",
                url,
                exc,
            )
            return None

        content_type = (
            response.headers
            .get("Content-Type", "")
            .lower()
        )

        if (
            content_type
            and "text/html" not in content_type
            and "application/xhtml+xml"
            not in content_type
        ):
            logger.debug(
                "Rejected non-HTML response from %s: %s",
                response.url,
                content_type,
            )
            return None

        html = response.text

        if not html or not html.strip():
            return None

        if len(html) < 100:
            logger.debug(
                "Rejected unusually short HTML response from %s",
                response.url,
            )
            return None

        final_url = self._normalize_result_url(
            response.url
        )

        if not final_url:
            return None

        return final_url, html

    @staticmethod
    def _candidate_sort_key(
        candidate: RankedCandidate,
    ) -> tuple[int, int, int, int]:
        """
        Produce deterministic ranking order.

        Priority:
            1. Combined score
            2. Domain bonus
            3. Search-result score
            4. Higher search-engine position
        """

        return (
            candidate.total_score,
            candidate.domain_bonus,
            candidate.search_score,
            -candidate.search_result.position,
        )

    @staticmethod
    def _normalize_result_url(
        url: str | None,
    ) -> str | None:
        """
        Normalize a search-result URL.

        Adds an HTTPS scheme when the provider returns a bare domain.
        Removes URL fragments.
        """

        if not url:
            return None

        value = url.strip()

        if not value:
            return None

        if value.startswith("//"):
            value = f"https:{value}"

        if "://" not in value:
            value = f"https://{value}"

        try:
            parsed = urlparse(value)
        except ValueError:
            return None

        if parsed.scheme.lower() not in {
            "http",
            "https",
        }:
            return None

        if not parsed.hostname:
            return None

        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            fragment="",
        )

        return urlunparse(normalized)

    @staticmethod
    def _to_homepage_url(
        url: str,
    ) -> str | None:
        """
        Convert a result URL into a root homepage URL.

        Search engines frequently return an About, Contact, Product, or
        article URL. Official-company validation should start at the
        site's root homepage.
        """

        try:
            parsed = urlparse(url)
        except ValueError:
            return None

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return None

        if not parsed.hostname:
            return None

        homepage = parsed._replace(
            path="/",
            params="",
            query="",
            fragment="",
        )

        return urlunparse(homepage)

    @staticmethod
    def _provider_name(
        provider: SearchProvider,
    ) -> str:
        """
        Return a readable provider name for logs.
        """

        configured_name = getattr(
            provider,
            "name",
            None,
        )

        if configured_name:
            return str(configured_name)

        return provider.__class__.__name__