from automation.intelligence.search_engine import SearchEngine
from automation.resolvers.providers.zenserp_provider import ZenserpProvider
from automation.resolvers.providers.base import SearchResult


class ZenserpSearchEngine(SearchEngine):

    def __init__(self):
        self.provider = ZenserpProvider()

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        return self.provider.search(query)