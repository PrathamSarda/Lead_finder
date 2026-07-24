import re
from urllib.parse import urlparse

from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)
from automation.intelligence.utils.normalizations import normalize_url


class LinkedInExtractor:
    """
    Convert LinkedIn company-page search results into structured evidence.
    """

    COMPANY_PATH_PATTERN = re.compile(
        r"^/company/[^/?#]+/?$",
        re.IGNORECASE,
    )

    WEBSITE_PATTERN = re.compile(
        r"(?:website\s*:?\s*)(https?://[^\s,;]+|www\.[^\s,;]+|"
        r"[a-z0-9][a-z0-9.-]+\.[a-z]{2,})",
        re.IGNORECASE,
    )

    def can_extract(
        self,
        collected: CollectedResult,
    ) -> bool:
        """
        Return True only for LinkedIn company-profile URLs.
        """

        parsed = urlparse(collected.result.url)

        hostname = parsed.netloc.lower()

        if not (
            hostname == "linkedin.com"
            or hostname.endswith(".linkedin.com")
        ):
            return False

        return bool(
            self.COMPANY_PATH_PATTERN.match(parsed.path)
        )

    def extract(
        self,
        company: CompanyInput,
        collected: CollectedResult,
    ) -> CompanyEvidence | None:
        """
        Create structured evidence from a LinkedIn company result.
        """
        print(collected.result.url)
        if not self.can_extract(collected):
            return None

        result = collected.result

        combined_text = " ".join(
            part
            for part in [
                result.title,
                result.snippet,
            ]
            if part
        )

        website = self._extract_website(combined_text)

        confidence = self._calculate_confidence(
            company=company,
            title=result.title,
            snippet=result.snippet,
        )

        return CompanyEvidence(
            source="linkedin",
            title=result.title,
            url=normalize_url(result.url),
            snippet=result.snippet,
            company_name=result.title or company.name,
            website=website,
            confidence=confidence,
        )

    def _extract_website(
        self,
        text: str,
    ) -> str | None:
        """
        Extract a website/domain mentioned in LinkedIn search text.
        """

        match = self.WEBSITE_PATTERN.search(text)

        if not match:
            return None

        website = match.group(1).rstrip(".,);]")

        if website.startswith("www."):
            return f"https://{website}"

        if not website.startswith(("http://", "https://")):
            return f"https://{website}"

        return website

    def _calculate_confidence(
        self,
        company: CompanyInput,
        title: str,
        snippet: str,
    ) -> float:
        """
        Calculate a basic confidence score using company-name similarity.
        """

        expected_tokens = self._company_tokens(company.name)

        result_tokens = self._company_tokens(
            f"{title} {snippet}"
        )

        if not expected_tokens:
            return 0.0

        matched_tokens = expected_tokens.intersection(
            result_tokens
        )

        token_score = len(matched_tokens) / len(
            expected_tokens
        )

        if token_score == 1.0:
            return 0.95

        if token_score >= 0.75:
            return 0.85

        if token_score >= 0.5:
            return 0.65

        return 0.35

    @staticmethod
    def _company_tokens(
        value: str,
    ) -> set[str]:
        """
        Normalize a company name into meaningful comparison tokens.
        """

        ignored_tokens = {
            "inc",
            "incorporated",
            "llc",
            "ltd",
            "limited",
            "corp",
            "corporation",
            "company",
            "co",
            "the",
        }

        tokens = re.findall(
            r"[a-z0-9]+",
            value.lower(),
        )

        return {
            token
            for token in tokens
            if token not in ignored_tokens
        }
