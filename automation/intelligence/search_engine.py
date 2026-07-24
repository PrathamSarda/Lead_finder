from abc import ABC, abstractmethod

from automation.resolvers.providers.base import SearchResult


class SearchEngine(ABC):

    @abstractmethod
    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        ...
