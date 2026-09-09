from __future__ import annotations

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
        backend: str = "duckduckgo",
    ) -> None:
        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        self.max_results = max_results
        self.region = region
        self.safesearch = safesearch
        # Pinned to the duckduckgo backend deliberately. The ddgs
        # library's default "auto" backend fans out across several
        # other search engines' own result pages (Google, Yahoo,
        # Brave, Startpage, Mojeek) when one is slow/blocked, which
        # is both much slower and a real risk of getting this IP
        # rate-limited or blocked by those engines. A single,
        # consistent backend is safer and faster.
        self.backend = backend

    def search(self, query: str) -> list[SearchResult]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        try:
            with DDGS() as ddgs:
                raw_results = list(
                    ddgs.text(
                        normalized_query,
                        region=self.region,
                        safesearch=self.safesearch,
                        max_results=self.max_results,
                        backend=self.backend,
                    )
                )

        except Exception as exc:
            raise DDGSSearchError(
                f"DDGS search failed for query "
                f"{normalized_query!r}: {exc}"
            ) from exc

        return self._normalize_results(raw_results)

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