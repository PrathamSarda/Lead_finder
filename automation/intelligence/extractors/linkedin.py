from __future__ import annotations

import re
from urllib.parse import urlparse

from automation.intelligence.extractors.base import BaseExtractor
from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)


class LinkedInExtractor(BaseExtractor):
    """
    Extract structured company evidence from LinkedIn search results.
    """

    @property
    def source_name(self) -> str:
        return "linkedin"

    @property
    def default_confidence(self) -> float:
        return 0.95

    def can_extract(
        self,
        collected_result: CollectedResult,
    ) -> bool:

        url = (collected_result.result.url or "").strip()

        if not url:
            return False

        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        hostname = (parsed.hostname or "").lower()

        if hostname == "linkedin.com" or hostname.endswith(".linkedin.com"):
            hostname = "linkedin.com"

        return (
            hostname == "linkedin.com"
            and parsed.path.startswith("/company/")
        )

    def extract(
        self,
        company: CompanyInput,
        collected_results: list[CollectedResult],
    ) -> list[CompanyEvidence]:

        evidence: list[CompanyEvidence] = []

        for result in self.supported_results(collected_results):

            website = self._extract_website(
                result.result.snippet
            )

            company_name = (
                result.result.title.strip()
                if result.result.title
                else company.name
            )

            evidence.append(
                self.build_evidence(
                    title=result.result.title,
                    url=result.result.url,
                    snippet=result.result.snippet,
                    company_name=company_name,
                    website=website,
                )
            )

        return evidence

    @staticmethod
    def _extract_website(
        snippet: str,
    ) -> str | None:

        if not snippet:
            return None

        match = re.search(
            r"https?://[^\s;]+",
            snippet,
            re.IGNORECASE,
        )

        if match:
            return match.group(0).rstrip(".,;)")

        return None