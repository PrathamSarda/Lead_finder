from dataclasses import dataclass
from automation.resolvers.providers.base import SearchResult



@dataclass(slots=True)
class CompanyInput:
    name: str
    city: str | None = None
    state: str | None = None


@dataclass(slots=True)
class CompanyEvidence:
    source: str

    title: str
    url: str
    snippet: str

    company_name: str | None = None

    website: str | None = None

    email: str | None = None

    phone: str | None = None

    location: str | None = None

    confidence: float = 0.0


@dataclass(slots=True)
class SearchQuery:
    source: str
    query: str
    priority: int
@dataclass(slots=True)
class CollectedResult:
    query: SearchQuery
    result: SearchResult