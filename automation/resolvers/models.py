from __future__ import annotations

from dataclasses import dataclass

from automation.resolvers.providers.base import SearchResult


@dataclass(slots=True, frozen=True)
class RankedCandidate:
    """
    A search result after filtering and scoring.
    """

    search_result: SearchResult
    normalized_url: str
    search_score: int
    domain_bonus: int
    total_score: int


@dataclass(slots=True, frozen=True)
class ResolutionResult:
    """
    Final output returned by WebsiteResolver.
    """

    found: bool

    website: str | None = None
    provider: str | None = None
    score: int = 0
    validated: bool = False

    search_result: SearchResult | None = None

    reason: str | None = None
    attempted_candidates: int = 0