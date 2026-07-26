from automation.intelligence.models import (
    CompanyInput,
    SearchQuery,
)
from automation.resolvers.providers.base import SearchProviderError
from automation.intelligence.query_builder import QueryBuilder
from automation.intelligence.search_engine import SearchEngine

from automation.intelligence.utils.normalizations import (
    normalize_url,
)
from automation.intelligence.models import (
    CompanyInput,
    CollectedResult,
)

class EvidenceCollector:

    def __init__(
        self,
        search_engine: SearchEngine,
    ) -> None:

        self.search_engine = search_engine
        self.query_builder = QueryBuilder()

    def collect_queries(
    self,
    queries: list[SearchQuery],
):


        all_results = []

        seen_urls = set()

        for query in queries:

            try:
                results = self.search_engine.search(query.query)

            except SearchProviderError:
                ...
                continue

            for result in results:

                normalized = normalize_url(result.url)

                if normalized in seen_urls:
                    continue

                seen_urls.add(normalized)

                all_results.append(
                CollectedResult(
                query=query,
                result=result,
                )
            )

        return all_results   

    def collect_stage(
    self,
    company: CompanyInput,
    stage: int,
):
        queries = self.query_builder.build_stage(
            company,
            stage,
        )

        return self.collect_queries(
            queries,
        )

    def collect(
    self,
    company: CompanyInput,
):
        """
        Backwards-compatible helper.
        """

        queries = self.query_builder.build(company)

        return self.collect_queries(queries)  