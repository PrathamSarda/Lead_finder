
from __future__ import annotations

from automation.intelligence.evidence_collector import EvidenceCollector
from automation.intelligence.evidence_merger import EvidenceMerger
from automation.intelligence.extractors.generic import GenericExtractor
from automation.intelligence.extractors.indeed import IndeedExtractor
from automation.intelligence.extractors.linkedin import LinkedInExtractor
from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)
from automation.intelligence.query_builder import QueryBuilder
from automation.intelligence.result_filter import ResultFilter
from automation.intelligence.search_engine import SearchEngine
from automation.intelligence.ddgs_search_engine import DDGSSearchEngine
from automation.intelligence.zenserp_search_engine import ZenserpSearchEngine


class CompanyPipeline:
    """End-to-end intelligence pipeline using the top 3 filtered results."""

    MAX_RESULTS_PER_COMPANY = 6

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
    ) -> None:
        if search_engine is None:
            search_engine = DDGSSearchEngine()

        self.query_builder = QueryBuilder()
        self.collector = EvidenceCollector(search_engine)
        self.filter = ResultFilter()

        self.extractors = (
            LinkedInExtractor(),
            IndeedExtractor(),
            GenericExtractor(),
        )

        self.merger = EvidenceMerger()

        # Holds the final top candidates for inspection after each run.
        self.last_candidates: list[CollectedResult] = []

    def run(
        self,
        company: CompanyInput,
    ) -> CompanyEvidence | None:
        collected_all: list[CollectedResult] = []

        # Collect search results from every query stage.
        for stage in range(self.query_builder.stage_count()):
            print(f"\n========== Stage {stage} ==========")

            collected = self.collector.collect_stage(
                company,
                stage,
            )

            print(f"Results collected in stage {stage}: {len(collected)}")
            collected_all.extend(collected)

        if not collected_all:
            print("No search results collected.")
            self.last_candidates = []
            return None

        # Filter and rank all results together, then retain the top candidates.
        filtered = self.filter.filter(
            company,
            collected_all,
        )

        # Prioritize keeping both official website candidates and directory/social profiles
        website_candidates = [c for c in filtered if c.query.source == "website"]
        other_candidates = [c for c in filtered if c.query.source != "website"]

        # Interleave or combine to ensure the actual website is never crowded out
        top_candidates = []
        if website_candidates:
            top_candidates.extend(website_candidates[:3])
        top_candidates.extend(other_candidates[:3])
        if len(top_candidates) < self.MAX_RESULTS_PER_COMPANY:
            for c in filtered:
                if c not in top_candidates and len(top_candidates) < self.MAX_RESULTS_PER_COMPANY:
                    top_candidates.append(c)

        self.last_candidates = top_candidates

        print("\n--- TOP CANDIDATES ---")
        for index, item in enumerate(top_candidates, start=1):
            print(
                f"{index}. {item.result.title}"
                f" | {item.result.url}"
                f" | Destination: {getattr(item.result, 'destination', None)}"
            )
        print("--- END TOP CANDIDATES ---")

        if not top_candidates:
            print("No results passed the filter.")
            return None

        # Run the existing extractors on the same top 3 candidates.
        evidence: list[CompanyEvidence] = []

        for extractor in self.extractors:
            evidence.extend(
                extractor.extract(
                    company,
                    top_candidates,
                )
            )

        if not evidence:
            print("No company evidence extracted from the top candidates.")
            return None

        print("\n--- EXTRACTED EVIDENCE ---")
        for item in evidence:
            print(
                f"{item.source:10}"
                f" | {item.company_name}"
                f" | {item.website}"
                f" | Email: {item.email}"
                f" | Phone: {item.phone}"
                f" | Confidence: {item.confidence}"
            )
        print("--- END EXTRACTED EVIDENCE ---")

        # Merge once after all selected candidates have been processed.
        merged = self.merger.merge(evidence)

        if merged is None:
            print("Evidence could not be merged.")
            return None

        print("\n--- FINAL MERGED RESULT ---")
        print("Company:", merged.company_name or company.name)
        print("Website:", merged.website)
        print("Email:", merged.email)
        print("Phone:", merged.phone)
        print("Location:", merged.location)
        print("Sources:", merged.sources)
        print("--- END FINAL RESULT ---")

        return merged