from dataclasses import dataclass
from automation.resolvers.providers.base import SearchResult



@dataclass(slots=True)
class CompanyInput:
    name: str
    city: str | None = None
    state: str | None = None


@dataclass(slots=True)
class CompanyEvidence:
    """
    Structured evidence extracted from a single search result.
    """

    # Source that produced this evidence
    source: str

    # Original search result
    title: str
    url: str
    snippet: str

    # Structured company information
    company_name: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None

    # Provenance source URLs
    website_source_url: str | None = None
    email_source_url: str | None = None
    phone_source_url: str | None = None

    # Verification status & reason
    status: str | None = None
    status_reason: str | None = None

    # Confidence assigned by the extractor
    confidence: float = 0.0

    # Sources that contributed to the merged result
    sources: list[str] | None = None



    def __post_init__(self) -> None:
        # Keep confidence within [0, 1]
        self.confidence = max(
            0.0,
            min(float(self.confidence), 1.0),
        )

        # Normalize whitespace for all string fields
        for field in (
            "source",
            "title",
            "url",
            "snippet",
            "company_name",
            "website",
            "email",
            "phone",
            "location",
            "website_source_url",
            "email_source_url",
            "phone_source_url",
            "status",
            "status_reason",
        ):
            value = getattr(self, field)

            if isinstance(value, str):
                cleaned = " ".join(value.split())

                if cleaned == "":
                    cleaned = None if field not in {
                        "source",
                        "title",
                        "url",
                        "snippet",
                    } else ""

                setattr(self, field, cleaned)

@dataclass(slots=True)
class SearchQuery:
    """
    Represents a search query generated for a specific source.
    """

    source: str
    query: str
    priority: int = 1


@dataclass(slots=True)
class CollectedResult:
    query: SearchQuery
    result: SearchResult