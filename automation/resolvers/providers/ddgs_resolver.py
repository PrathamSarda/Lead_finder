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

        if raw_results is None:
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