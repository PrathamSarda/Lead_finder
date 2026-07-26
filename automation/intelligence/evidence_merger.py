from __future__ import annotations

from automation.intelligence.models import CompanyEvidence


class EvidenceMerger:
    """
    Merge multiple CompanyEvidence objects into one canonical record.
    """

    def merge(
        self,
        evidence_list: list[CompanyEvidence],
    ) -> CompanyEvidence | None:

        if not evidence_list:
            return None

        # Highest confidence first
        ordered = sorted(
            evidence_list,
            key=lambda item: item.confidence,
            reverse=True,
        )

        best = ordered[0]

        merged = CompanyEvidence(
            source=best.source,
            title=best.title,
            url=best.url,
            snippet=best.snippet,
            company_name=best.company_name,
            website=best.website,
            email=best.email,
            phone=best.phone,
            location=best.location,
            confidence=best.confidence,
        )

        # Merge missing fields
        for item in ordered[1:]:

            if not merged.company_name and item.company_name:
                merged.company_name = item.company_name

            if not merged.website and item.website:
                merged.website = item.website

            if not merged.email and item.email:
                merged.email = item.email

            if not merged.phone and item.phone:
                merged.phone = item.phone

            if not merged.location and item.location:
                merged.location = item.location

        merged.sources = self._collect_sources(
            evidence_list,
        )

        return merged

    @staticmethod
    def _collect_sources(
        evidence_list: list[CompanyEvidence],
    ) -> list[str]:

        sources = []

        for item in evidence_list:

            if item.source not in sources:
                sources.append(item.source)

        return sorted(sources)