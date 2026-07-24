from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)


class BaseExtractor(ABC):
    """
    Base class for all evidence extractors.

    Responsibilities:

    - Determine whether a search result belongs to this extractor.
    - Extract structured CompanyEvidence.
    - Provide common helper methods.
    """

    DEFAULT_CONFIDENCE = 0.80

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique source name."""
        raise NotImplementedError

    @property
    def default_confidence(self) -> float:
        """Default confidence for evidence produced by this extractor."""
        return self.DEFAULT_CONFIDENCE

    @abstractmethod
    def can_extract(
        self,
        collected_result: CollectedResult,
    ) -> bool:
        """Return True if this extractor supports the search result."""
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        company: CompanyInput,
        collected_results: list[CollectedResult],
    ) -> list[CompanyEvidence]:
        """Extract evidence from supported search results."""
        raise NotImplementedError

    def supported_results(
        self,
        collected_results: Iterable[CollectedResult],
    ) -> list[CollectedResult]:
        """
        Return only the search results that belong to this extractor.
        """
        return [
            result
            for result in collected_results
            if self.can_extract(result)
        ]

    def build_evidence(
        self,
        *,
        confidence: float | None = None,
        **kwargs,
    ) -> CompanyEvidence:
        """
        Build a CompanyEvidence object with consistent metadata.
        """

        if confidence is None:
            confidence = self.default_confidence

        confidence = max(
            0.0,
            min(float(confidence), 1.0),
        )

        cleaned = {}

        for key, value in kwargs.items():
            if isinstance(value, str):
                value = self.normalize_whitespace(value)

                if value == "":
                    value = None

            cleaned[key] = value

        return CompanyEvidence(
        source=self.source_name,
        title=cleaned.get("title", ""),
        url=cleaned.get("url", ""),
        snippet=cleaned.get("snippet", ""),
        company_name=cleaned.get("company_name"),
        website=cleaned.get("website"),
        email=cleaned.get("email"),
        phone=cleaned.get("phone"),
        location=cleaned.get("location"),
        confidence=confidence,
        )

    @staticmethod
    def first_non_empty(
        *values: str | None,
    ) -> str:
        for value in values:
            if value and value.strip():
                return value.strip()

        return ""

    @staticmethod
    def normalize_whitespace(
        value: str | None,
    ) -> str:
        if not value:
            return ""

        return " ".join(value.split())