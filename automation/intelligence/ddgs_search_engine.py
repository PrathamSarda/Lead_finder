from automation.intelligence.search_engine import SearchEngine
from automation.resolvers.providers.ddgs_resolver import DDGSProvider
from automation.resolvers.providers.base import SearchResult


class DDGSSearchEngine(SearchEngine):

    def __init__(self):
        self.provider = DDGSProvider()

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        return self.provider.search(query)
