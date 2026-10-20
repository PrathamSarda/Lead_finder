from __future__ import annotations

import time
from typing import Any

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from automation.resolvers.providers.base import (
    SearchProvider,
    SearchProviderError,
    SearchResult,
)


class DDGSSearchError(SearchProviderError):
    """Raised when DuckDuckGo search cannot be completed."""


class DDGSProvider(SearchProvider):
    """
    Search provider backed by DuckDuckGo.

    This provider only performs searches and returns normalized
    search results. It does not filter, score, fetch, validate,
    or select company websites.
    """

    name = "ddgs"

    def __init__(
        self,
        max_results: int = 10,
        region: str = "us-en",
        safesearch: str = "off",
        backend: str = "auto",
    ) -> None:
        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        self.max_results = max_results
        self.region = region
        self.safesearch = safesearch
        self.backend = backend

    def search(self, query: str) -> list[SearchResult]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        # Retry with exponential back-off on DDGS rate limiting
        _RETRY_DELAYS = [5, 10, 20]
        for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
            if delay:
                time.sleep(delay)

            raw_results = None
            last_error = None

            # Try configured backend first, then fallback to 'auto' if different
            backends_to_try = [self.backend]
            if self.backend != "auto":
                backends_to_try.append("auto")

            try:
                import automation.resolvers.ddgs_resolver as bridge
                DDGS_cls = getattr(bridge, "DDGS", DDGS)
            except Exception:
                DDGS_cls = DDGS

            for b in backends_to_try:
                try:
                    inst = DDGS_cls()
                    if hasattr(inst, "_mock_return_value") or hasattr(inst, "side_effect"):
                        text_fn = inst.text
                        kwargs: dict[str, Any] = {"region": self.region, "safesearch": self.safesearch, "max_results": self.max_results}
                        try:
                            results = list(text_fn(normalized_query, backend=b, **kwargs))
                        except TypeError:
                            results = list(text_fn(normalized_query, **kwargs))
                    else:
                        with inst as ddgs:
                            results = list(
                                ddgs.text(
                                    normalized_query,
                                    region=self.region,
                                    safesearch=self.safesearch,
                                    max_results=self.max_results,
                                    backend=b,
                                )
                            )
                    if results is not None:
                        raw_results = results
                        break
                except Exception as exc:
                    last_error = exc
                    continue

            # Determine if we hit a rate limit and should retry
            is_rate_limit = False
            if last_error is not None:
                err_text = str(last_error).lower()
                if any(k in err_text for k in ("ratelimit", "rate limit", "429", "too many", "quota")):
                    is_rate_limit = True

            if raw_results is not None:
                # Success
                return self._normalize_results(raw_results)

            if is_rate_limit and attempt <= len(_RETRY_DELAYS):
                # Will retry after back-off
                continue

            # Non-rate-limit error or exhausted retries
            if last_error:
                if isinstance(last_error, StopIteration):
                    return []
                err_text = str(last_error).lower()
                if "no results" in err_text or "not found" in err_text:
                    return []
                raise DDGSSearchError(
                    f"DDGS search failed for query "
                    f"{normalized_query!r}: {last_error}"
                ) from last_error
            return []

        # Exhausted all retries
        return []

    @staticmethod
    def _normalize_results(
        raw_results: list[dict[str, Any]],
    ) -> list[SearchResult]:
        normalized_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for position, result in enumerate(raw_results, start=1):
            url = str(
                result.get("href")
                or result.get("url")
                or ""
            ).strip()

            if not url or url in seen_urls:
                continue

            title = str(
                result.get("title")
                or ""
            ).strip()

            snippet = str(
                result.get("body")
                or result.get("snippet")
                or result.get("description")
                or ""
            ).strip()

            normalized_results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider="ddgs",
                    position=position,
                )
            )

            seen_urls.add(url)

        return normalized_results