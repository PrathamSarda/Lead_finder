from automation.intelligence.models import CompanyInput
from automation.intelligence.evidence_collector import (
    EvidenceCollector,
)
from automation.intelligence.zenserp_search_engine import (
    ZenserpSearchEngine,
)

collector = EvidenceCollector(
    ZenserpSearchEngine()
)

company = CompanyInput(
    name="BROCKMAN TRUCKING INC"
)

results = collector.collect(company)

print()

print("=" * 80)
print(f"Collected {len(results)} unique search results")
print("=" * 80)

for item in results:

    query = item.query
    result = item.result

    print()

    print(query.source)
    print(result.title)
    print(result.url)