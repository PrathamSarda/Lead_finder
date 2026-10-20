from __future__ import annotations

import logging
import re
import time
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
from automation.resolvers.providers.zenserp_provider import (
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
from automation.verification.directory_registry import normalize_domain


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
        acceptance_threshold: int = 70,  # lowered to accept more candidates
        request_timeout: float = 7.0,
        max_validation_candidates: int = 12,  # increased to validate more candidates
        max_results_per_provider: int = 80,  # increased pool of raw results
        min_results_before_broader_query: int = 5,
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

        if min_results_before_broader_query <= 0:
            raise ValueError(
                "min_results_before_broader_query must be "
                "greater than zero."
            )

        if providers is not None:
            self.providers = providers
        else:
            default_providers: list[SearchProvider] = [DDGSProvider()]
            try:
                default_providers.append(ZenserpProvider())
            except Exception:
                pass
            self.providers = default_providers

        self.acceptance_threshold = acceptance_threshold
        self.request_timeout = request_timeout
        self.max_validation_candidates = (
            max_validation_candidates
        )
        self.max_results_per_provider = (
            max_results_per_provider
        )
        self.min_results_before_broader_query = (
            min_results_before_broader_query
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
        rejected_candidates: list[str] = []
        validated_candidates: list[str] = []
        top_candidates_meta: list[dict[str, str]] = []

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
                rejected_candidates=rejected_candidates,
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
                validated_candidates=validated_candidates,
                rejected_candidates=rejected_candidates,
            )

            total_attempted_candidates += (
                validation_result.attempted_candidates
            )

            top_candidates_meta = [
                {
                    "title": c.search_result.title,
                    "url": c.normalized_url,
                    "snippet": c.search_result.snippet or "",
                    "score": str(c.total_score),
                }
                for c in ranked_candidates[:5]
            ]

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
                    rejected_candidates=rejected_candidates,
                    validated_candidates=validated_candidates,
                    candidate_results=top_candidates_meta,
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
            rejected_candidates=rejected_candidates,
            validated_candidates=validated_candidates,
            candidate_results=top_candidates_meta,
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
        last_error = None
        consecutive_timeouts = 0

        # Memory cache on resolver instance across calls
        if not hasattr(self, "_query_cache"):
            self._query_cache: dict[tuple[str, str], list[SearchResult]] = {}
        if not hasattr(self, "_failed_queries"):
            self._failed_queries: set[tuple[str, str]] = set()

        p_name = self._provider_name(provider)

        for query_idx, query in enumerate(queries):
            if len(results) >= self.max_results_per_provider:
                break

            cache_key = (p_name, query)
            if cache_key in self._query_cache:
                logger.debug("Cache hit for %s query %r", p_name, query)
                query_results = self._query_cache[cache_key]
            elif cache_key in self._failed_queries:
                logger.debug("Skipping known failed query for %s: %r", p_name, query)
                continue
            else:
                if (
                    results
                    and len(results)
                    >= self.min_results_before_broader_query
                    and self._has_strong_candidate(results, company_name)
                ):
                    logger.debug(
                        "Stopping query fan-out for %s after %d "
                        "result(s); strong candidate found.",
                        p_name,
                        len(results),
                    )
                    break

                # Inter-query throttling: rate limit requests to prevent HTTP 429/502
                if query_idx > 0:
                    time.sleep(1.0)

                logger.debug(
                    "Searching provider %s with query: %s",
                    p_name,
                    query,
                )

                try:
                    query_results = provider.search(query)
                    consecutive_timeouts = 0
                    self._query_cache[cache_key] = query_results
                except Exception as exc:
                    last_error = exc
                    self._failed_queries.add(cache_key)
                    err_lower = str(exc).lower()
                    if any(k in err_lower for k in ("not enough requests", "quota", "rate limit", "403", "429", "throttled", "auto-throttled", "502")):
                        logger.warning(
                            "%s quota/rate-limit reached, stopping further queries: %s",
                            p_name,
                            exc,
                        )
                        break

                    if any(k in err_lower for k in ("timed out", "timeout")):
                        consecutive_timeouts += 1
                        if consecutive_timeouts >= 2:
                            logger.warning(
                                "%s timed out consecutively (%d times), stopping further queries: %s",
                                p_name,
                                consecutive_timeouts,
                                exc,
                            )
                            break

                    logger.warning(
                        "%s query %r failed: %s",
                        self._provider_name(provider),
                        query,
                        exc,
                    )
                    continue

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

        # Snippet URL mining: extract plain domain/URL mentions from snippet text of directory
        # results. Many directory pages (e.g. mckeesrocks.org) embed the actual company website
        # inside their snippet: "Business Website Address www.acmeclay.com". We inject these
        # as synthetic candidates so they enter scoring + validation even though the directory
        # result itself would be rejected by candidate_filter.
        snippet_injected: list[SearchResult] = []
        for result in results:
            snippet_urls = self._extract_urls_from_snippet(
                result.snippet, result.title
            )
            for surl in snippet_urls:
                norm = self._normalize_result_url(surl)
                if not norm:
                    continue
                ident = norm.lower()
                if ident in seen_urls:
                    continue
                seen_urls.add(ident)
                # Synthetic result inherits the original snippet for scoring context
                snippet_injected.append(
                    SearchResult(
                        title=result.title,
                        url=norm,
                        snippet=result.snippet,
                        provider=result.provider,
                        position=result.position,
                    )
                )

        # Prepend snippet-injected candidates so they are scored and validated
        results = snippet_injected + results

        return results

    def _rank_candidates(
        self,
        company_name: str,
        location: str | None,
        search_results: Iterable[SearchResult],
        rejected_candidates: list[str] | None = None,
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
                if rejected_candidates is not None:
                    rejected_candidates.append(result.url)
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
                if rejected_candidates is not None:
                    rejected_candidates.append(homepage_url)
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
        validated_candidates: list[str] | None = None,
        rejected_candidates: list[str] | None = None,
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
                if rejected_candidates is not None:
                    rejected_candidates.append(
                        candidate.normalized_url
                    )
                continue

            final_url, html = fetched_page

            # Guard against cross-domain redirects to completely unrelated domains
            # e.g. americanindustrialconstruction.com -> leecontracting.com
            orig_domain = normalize_domain(candidate.normalized_url)
            final_domain = normalize_domain(final_url)
            if orig_domain and final_domain and orig_domain != final_domain:
                orig_parts = orig_domain.split(".")
                final_parts = final_domain.split(".")
                orig_sld = ".".join(orig_parts[-2:]) if len(orig_parts) >= 2 else orig_domain
                final_sld = ".".join(final_parts[-2:]) if len(final_parts) >= 2 else final_domain
                if orig_sld != final_sld:
                    # SLDs differ; verify if the final domain matches the company name
                    from automation.resolvers.domain_similarity import calculate_domain_similarity
                    if calculate_domain_similarity(company_name, final_url) < 0.40:
                        logger.debug(
                            "Candidate %s redirected to unrelated domain %s; rejected",
                            candidate.normalized_url,
                            final_url,
                        )
                        if rejected_candidates is not None:
                            rejected_candidates.append(final_url)
                        continue

            filter_result = evaluate_candidate_url(
                final_url
            )

            if not filter_result.accepted:
                logger.debug(
                    "Candidate redirected to rejected URL %s: %s",
                    final_url,
                    filter_result.reason,
                )
                if rejected_candidates is not None:
                    rejected_candidates.append(final_url)
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
                if rejected_candidates is not None:
                    rejected_candidates.append(final_url)
                continue

            resolved_url = self._to_homepage_url(
                final_url
            )

            if validated_candidates is not None:
                validated_candidates.append(resolved_url)

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
                rejected_candidates=rejected_candidates or [],
                validated_candidates=validated_candidates or [resolved_url],
            )

        return ResolutionResult(
            found=False,
            reason="provider_candidates_failed_validation",
            attempted_candidates=attempted_candidates,
            rejected_candidates=rejected_candidates or [],
            validated_candidates=validated_candidates or [],
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
            # Fallback with simple User-Agent header if session gets blocked or 403
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=self.request_timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
            except requests.RequestException:
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

    @staticmethod
    def _has_strong_candidate(
        results: list[SearchResult],
        company_name: str,
    ) -> bool:
        """
        Return True if any of the search results appears to be a strong
        match for the company's official domain.

        A "strong" match means the company's key tokens appear in the
        hostname of the search result URL.
        """
        import re as _re
        from urllib.parse import urlparse as _urlparse

        EXCLUDED = {
            "linkedin", "facebook", "youtube", "twitter", "x",
            "yelp", "yellowpages", "manta", "bbb", "crunchbase",
            "zoominfo", "dnb", "bloomberg", "glassdoor", "indeed",
        }

        legal = {
            "inc", "llc", "ltd", "corp", "co", "company", "lp", "llp",
            "incorporated", "limited", "corporation", "pllc",
        }
        tokens = [
            t for t in _re.findall(r"[a-z0-9]+", company_name.lower())
            if t not in legal and len(t) >= 3
        ]

        if not tokens:
            return False

        for result in results:
            try:
                host = (_urlparse(result.url).hostname or "").lower().removeprefix("www.")
            except Exception:
                continue

            if any(ex in host for ex in EXCLUDED):
                continue

            hostname_clean = _re.sub(r"[^a-z0-9]", "", host.split(".")[0])
            matches = sum(1 for t in tokens if t in hostname_clean)
            joined = "".join(tokens)

            if matches >= 2 or joined in hostname_clean:
                return True

        return False

    @staticmethod
    def _extract_urls_from_snippet(snippet: str | None, title: str = "") -> list[str]:
        """
        Extract plain URLs and domain-like patterns mentioned inside a search snippet.

        Many directory results (e.g. mckeesrocks.org) will include the actual company
        website inside their snippet text: "Business Website Address www.acmeclay.com".
        This method extracts such URLs so they can be injected as synthetic candidates.
        """
        if not snippet:
            return []

        found: list[str] = []
        seen: set[str] = set()

        # Match fully-qualified URLs (http[s]://...)
        full_url_pattern = re.compile(
            r"https?://(?:www\.)?[a-z0-9][-a-z0-9]*(?:\.[a-z0-9][-a-z0-9]*)+(?:/[^\s,;\"'<>]*)?"
            , re.IGNORECASE
        )
        # Match bare domain patterns like "www.acmeclay.com" or "acmeclay.com"
        bare_domain_pattern = re.compile(
            r"\bwww\.[a-z0-9][-a-z0-9]*(?:\.[a-z]{2,})+\b"
            r"|\b[a-z0-9][-a-z0-9]*\.(?:com|net|org|biz|us|info)\b",
            re.IGNORECASE
        )

        combined = f"{snippet} {title}"

        for m in full_url_pattern.finditer(combined):
            url = m.group(0).rstrip(".,;)")
            key = url.lower()
            if key not in seen:
                seen.add(key)
                found.append(url)

        for m in bare_domain_pattern.finditer(combined):
            raw = m.group(0).rstrip(".,;)")
            # Build a proper URL
            if raw.startswith("www.") or "://" not in raw:
                url = f"https://{raw}"
            else:
                url = raw
            key = url.lower()
            if key not in seen:
                seen.add(key)
                found.append(url)

        return found
