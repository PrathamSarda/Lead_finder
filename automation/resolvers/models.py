from __future__ import annotations

from dataclasses import dataclass, field

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
    rejected_candidates: list[str] = field(default_factory=list)
    validated_candidates: list[str] = field(default_factory=list)
    candidate_results: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_results, list):
            object.__setattr__(
                self,
                "candidate_results",
                list(self.candidate_results),
            )
        if not isinstance(self.rejected_candidates, list):
            object.__setattr__(
                self,
                "rejected_candidates",
                list(self.rejected_candidates),
            )
        if not isinstance(self.validated_candidates, list):
            object.__setattr__(
                self,
                "validated_candidates",
                list(self.validated_candidates),
            )

    @property
    def success(self) -> bool:
        return self.found