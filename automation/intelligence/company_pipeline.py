from __future__ import annotations

from automation.intelligence.evidence_collector import EvidenceCollector
from automation.intelligence.evidence_merger import EvidenceMerger
from automation.intelligence.extractors.generic import GenericExtractor
from automation.intelligence.extractors.indeed import IndeedExtractor
from automation.intelligence.extractors.linkedin import LinkedInExtractor
from automation.intelligence.models import (
    CompanyEvidence,
    CompanyInput,
)
from automation.intelligence.query_builder import QueryBuilder
from automation.intelligence.result_filter import ResultFilter
from automation.intelligence.search_engine import SearchEngine
from automation.intelligence.zenserp_search_engine import (
    ZenserpSearchEngine,
)


class CompanyPipeline:
    """
    End-to-end intelligence pipeline.
    """

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
    ) -> None:

        if search_engine is None:
            search_engine = ZenserpSearchEngine()

        self.query_builder = QueryBuilder()

        self.collector = EvidenceCollector(
            search_engine,
        )

        self.filter = ResultFilter()

        self.extractors = (
            LinkedInExtractor(),
            IndeedExtractor(),
            GenericExtractor(),
        )

        self.merger = EvidenceMerger()

    def run(
    self,
    company: CompanyInput,
) -> CompanyEvidence | None:

        merged: CompanyEvidence | None = None

        for stage in range(
            self.query_builder.stage_count()
        ):

            print(f"\n========== Stage {stage} ==========")

            collected = self.collector.collect_stage(
                company,
                stage,
            )

            if not collected:
                continue

            filtered = self.filter.filter(
                company,
                collected,
            )

            evidence: list[CompanyEvidence] = []

            for extractor in self.extractors:

                evidence.extend(
                    extractor.extract(
                        company,
                        filtered,
                    )
                )

            if not evidence:
                continue

            print("\nEvidence")
            print("-" * 80)

            for item in evidence:

                print(
                    f"{item.source:10}"
                    f" | {item.company_name}"
                    f" | {item.website}"
                    f" | {item.confidence}"
                )

            merged = self.merger.merge(
                evidence,
            )

            if merged is None:
                continue

            print("\nMerged website:", merged.website)

            #
            # EARLY STOP
            #
            if merged.website:

                print(
                    "\nOfficial website found."
                )

                print(
                    "Stopping further search stages."
                )

                return merged

        return merged