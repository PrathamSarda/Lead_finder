"""
Backward compatibility bridge for DDGS resolver tests and legacy imports.
"""
from __future__ import annotations
from typing import Any
from ddgs import DDGS
from automation.enrichment.website_fetcher import fetch_website
from automation.resolvers.providers.ddgs_resolver import DDGSProvider
from automation.resolvers.query_builder import build_search_queries as _canonical_build_queries
from automation.resolvers.website_resolver import WebsiteResolver
from automation.resolvers.models import ResolutionResult


def build_search_queries(company_name: str, location: str | None = None) -> list[str]:
    queries = _canonical_build_queries(company_name, location)
    if location and company_name:
        legacy_quote = f'"{company_name.strip()}" "{location.strip()}" website'
        if legacy_quote not in queries:
            queries.insert(1, legacy_quote)
    return queries


class DDGSWebsiteResolver(WebsiteResolver):
    def __init__(
        self,
        validation_limit: int = 8,
        query_delay_seconds: float = 0.0,
        **kwargs: Any,
    ) -> None:
        if query_delay_seconds < 0:
            raise ValueError("query_delay_seconds cannot be negative.")
        if validation_limit <= 0:
            raise ValueError("validation_limit must be greater than zero.")
        providers = kwargs.pop("providers", [DDGSProvider()])
        super().__init__(providers=providers, max_validation_candidates=validation_limit, **kwargs)
        self.query_delay_seconds = query_delay_seconds

    def _fetch_homepage(self, url: str) -> tuple[str, str] | None:
        import automation.resolvers.ddgs_resolver as bridge
        res = bridge.fetch_website(url)
        if res.success and res.html:
            return (res.final_url or url, res.html)
        return None

    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> ResolutionResult:
        if not company_name or not company_name.strip():
            return ResolutionResult(found=False, reason="empty_name")
        return super().resolve(company_name, location)


__all__ = [
    "DDGS",
    "DDGSProvider",
    "DDGSWebsiteResolver",
    "build_search_queries",
    "fetch_website",
]
