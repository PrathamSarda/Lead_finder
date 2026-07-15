from dataclasses import dataclass, field


@dataclass
class WebsiteResolutionResult:
    """
    Result returned by a website resolver.
    """

    success: bool

    website: str | None = None

    provider: str | None = None

    query: str | None = None

    checked_candidates: list[str] = field(
        default_factory=list
    )

    rejected_candidates: list[str] = field(
        default_factory=list
    )

    validated_candidates: list[str] = field(
        default_factory=list
    )

    error: str | None = None