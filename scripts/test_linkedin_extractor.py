from automation.intelligence.evidence_collector import (
    EvidenceCollector,
)
from automation.intelligence.extractors.linkedin import (
    LinkedInExtractor,
)
from automation.intelligence.models import CompanyInput
from automation.intelligence.zenserp_search_engine import (
    ZenserpSearchEngine,
)


company = CompanyInput(
    name="BROCKMAN TRUCKING INC",
    city="Afton",
    state="MN",
)

collector = EvidenceCollector(
    ZenserpSearchEngine()
)

extractor = LinkedInExtractor()

collected_results = collector.collect(company)
print("\nCollected results by source:")

for collected in collected_results:
    print(
        f"{collected.query.source}: "
        f"{collected.result.title} | "
        f"{collected.result.url}"
    )
linkedin_collected = [
    collected
    for collected in collected_results
    if collected.query.source == "linkedin"
]

print(
    f"\nRaw LinkedIn results collected: "
    f"{len(linkedin_collected)}"
)
evidence_items = []

for collected in collected_results:
    evidence = extractor.extract(
        company=company,
        collected=collected,
    )

    if evidence is not None:
        evidence_items.append(evidence)


print()
print("=" * 80)
print(f"LinkedIn evidence items: {len(evidence_items)}")
print("=" * 80)

for evidence in evidence_items:
    print()
    print(f"Source: {evidence.source}")
    print(f"Company: {evidence.company_name}")
    print(f"URL: {evidence.url}")
    print(f"Website: {evidence.website}")
    print(f"Confidence: {evidence.confidence}")
    print(f"Snippet: {evidence.snippet}")