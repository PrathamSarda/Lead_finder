from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    position: int
    destination: str | None = None


class SearchProviderError(RuntimeError):
    """Base exception for search-provider failures."""


class SearchProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str) -> list[SearchResult]:
        """Execute a search query and return normalized results."""
        raise NotImplementedError
