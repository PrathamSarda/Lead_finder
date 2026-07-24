from automation.intelligence.models import CompanyInput
from automation.intelligence.query_builder import QueryBuilder
from automation.intelligence.zenserp_search_engine import ZenserpSearchEngine


company = CompanyInput(
    name="BROCKMAN TRUCKING INC",
    city="Afton",
    state="Minnesota",
)

builder = QueryBuilder()
engine = ZenserpSearchEngine()

queries = builder.build(company)

for query in queries:

    print("=" * 80)
    print(query.source)
    print(query.query)
    print()

    results = engine.search(query.query)

    for result in results[:5]:
        print(result.title)
        print(result.url)
        print(result.snippet)
        print("-" * 40)