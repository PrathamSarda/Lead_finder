from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchFilters:
    """
    Represents the filters used when searching for companies
    across different lead sources.
    """

    country: str = "United States"

    employee_range: str = "1-15"

    industries: List[str] = field(default_factory=list)

    max_results: int = 100

    enabled_sources: List[str] = field(
        default_factory=lambda: [
            "google",
            "linkedin",
            "indeed",
            "wellfound"
        ]
    )