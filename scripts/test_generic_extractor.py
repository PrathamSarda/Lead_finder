from automation.intelligence.evidence_collector import (
    EvidenceCollector,
)
from automation.intelligence.extractors.generic import (
    GenericExtractor,
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

extractor = GenericExtractor()

collected_results = collector.collect(company)

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
print(f"Generic evidence items: {len(evidence_items)}")
print("=" * 80)

for evidence in evidence_items:
    print()
    print(f"Source: {evidence.source}")
    print(f"Title: {evidence.title}")
    print(f"URL: {evidence.url}")
    print(f"Website candidate: {evidence.website}")
    print(f"Email: {evidence.email}")
    print(f"Phone: {evidence.phone}")
    print(f"Confidence: {evidence.confidence}")