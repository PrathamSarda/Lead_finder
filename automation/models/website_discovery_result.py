from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WebsiteDiscoveryResult:
    """
    Result returned by the website discovery module.
    """

    success: bool

    website: Optional[str] = None

    checked_candidates: list[str] = field(
        default_factory=list
    )

    error: Optional[str] = None