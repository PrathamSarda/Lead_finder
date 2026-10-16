from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EnrichmentResult:
    """
    Structured result returned after enriching a company website.
    """

    website: str

    success: bool = False

    homepage_url: Optional[str] = None

    emails: list[str] = field(default_factory=list)

    phone_numbers: list[str] = field(default_factory=list)

    contact_pages: list[str] = field(default_factory=list)

    fetched_pages: list[str] = field(default_factory=list)

    failed_pages: list[str] = field(default_factory=list)

    error: Optional[str] = None

    email_sources: dict[str, str] = field(default_factory=dict)

    phone_sources: dict[str, str] = field(default_factory=dict)