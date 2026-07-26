from __future__ import annotations

from urllib.parse import urlparse

from automation.intelligence.extractors.base import BaseExtractor
from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)


class IndeedExtractor(BaseExtractor):

    EXCLUDED_PATHS = (
        "/jobs",
        "/viewjob",
        "/q-",
        "/m/",
    )

    PROFILE_KEYWORDS = (
        "/cmp/",
        "working-at",
        "reviews",
    )

    @property
    def source_name(self) -> str:
        return "indeed"

    @property
    def default_confidence(self) -> float:
        return 0.85

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

        if "indeed." not in hostname:
            return False

        path = parsed.path.lower()

        if any(
            path.startswith(prefix)
            for prefix in self.EXCLUDED_PATHS
        ):
            return False

        return any(
            keyword in path
            for keyword in self.PROFILE_KEYWORDS
        )

    def extract(
        self,
        company: CompanyInput,
        collected_results: list[CollectedResult],
    ) -> list[CompanyEvidence]:

        evidence: list[CompanyEvidence] = []

        seen_urls: set[str] = set()

        for collected_result in self.supported_results(collected_results):

            result = collected_result.result

            canonical = result.url.lower().rstrip("/")

            if canonical in seen_urls:
                continue

            seen_urls.add(canonical)

            company_name = self.first_non_empty(
                self._extract_company_name(result.title),
                company.name,
            )

            location = self._extract_location(
                result.snippet,
                company,
            )

            evidence.append(
                self.build_evidence(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    company_name=company_name,
                    location=location,
                    confidence=self.default_confidence,
                )
            )

        return evidence
    
    @staticmethod
    def _extract_company_name(
        title: str,
    ) -> str | None:

        if not title:
            return None

        title = title.strip()

        prefixes = (
            "Working at ",
            "Reviews from ",
        )

        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):]

        separators = (
            " | ",
            " - ",
            " — ",
            " – ",
        )

        for separator in separators:
            if separator in title:
                title = title.split(separator, 1)[0].strip()

        return title

    @staticmethod
    def _extract_location(
        snippet: str,
        company: CompanyInput,
    ) -> str | None:
        """
        Indeed snippets rarely contain reliable structured locations.
        For now we simply use the input company location as a fallback.
        """

        if company.city and company.state:
            return f"{company.city}, {company.state}"

        if company.city:
            return company.city

        if company.state:
            return company.state

        return None

        