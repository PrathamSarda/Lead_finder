import re
from urllib.parse import urlparse

from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)
from automation.intelligence.utils.normalization import (
    domain,
    normalize_url,
)


class GenericExtractor:
    """
    Extract useful evidence from general search results.

    This handles results returned by:
    - official website queries
    - contact queries
    - email queries
    - phone queries
    """

    EMAIL_PATTERN = re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    )

    PHONE_PATTERN = re.compile(
        r"""
        (?:
            \+?1[\s.\-()]*
        )?
        (?:
            \(\d{3}\)
            |
            \d{3}
        )
        [\s.\-]*
        \d{3}
        [\s.\-]*
        \d{4}
        """,
        re.VERBOSE,
    )

    BLOCKED_DOMAINS = {
        "linkedin.com",
        "indeed.com",
        "glassdoor.com",
        "clutch.co",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "youtube.com",
    }

    DIRECTORY_DOMAINS = {
        "zoominfo.com",
        "yellowpages.com",
        "datanyze.com",
        "rocketreach.co",
        "crunchbase.com",
        "whitepages.com",
        "roserocket.com",
        "lanefinder.com",
        "carriersource.io",
        "dispatchff.com",
        "safer.fmcsa.dot.gov",
    }

    def can_extract(
        self,
        collected: CollectedResult,
    ) -> bool:
        return collected.query.source in {
            "website",
            "contact",
            "email",
            "phone",
        }

    def extract(
        self,
        company: CompanyInput,
        collected: CollectedResult,
    ) -> CompanyEvidence | None:
        if not self.can_extract(collected):
            return None

        result = collected.result

        title = result.title or ""
        snippet = result.snippet or ""
        url = normalize_url(result.url)

        combined_text = f"{title} {snippet}"

        email = self._extract_email(combined_text)
        phone = self._extract_phone(combined_text)

        result_domain = domain(url)

        website = self._website_candidate(
            result_domain=result_domain,
            url=url,
        )

        confidence = self._calculate_confidence(
            company=company,
            title=title,
            snippet=snippet,
            result_domain=result_domain,
        )

        return CompanyEvidence(
            source=collected.query.source,
            title=title,
            url=url,
            snippet=snippet,
            company_name=company.name,
            website=website,
            email=email,
            phone=phone,
            confidence=confidence,
        )

    def _website_candidate(
        self,
        result_domain: str,
        url: str,
    ) -> str | None:
        if not result_domain:
            return None

        if result_domain in self.BLOCKED_DOMAINS:
            return None

        if result_domain in self.DIRECTORY_DOMAINS:
            return None

        return url

    def _extract_email(
        self,
        text: str,
    ) -> str | None:
        match = self.EMAIL_PATTERN.search(text)

        if match is None:
            return None

        return match.group(0).lower()

    def _extract_phone(
        self,
        text: str,
    ) -> str | None:
        match = self.PHONE_PATTERN.search(text)

        if match is None:
            return None

        phone = match.group(0).strip()

        digits = re.sub(r"\D", "", phone)

        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        if len(digits) != 10:
            return None

        return (
            f"({digits[:3]}) "
            f"{digits[3:6]}-"
            f"{digits[6:]}"
        )

    def _calculate_confidence(
        self,
        company: CompanyInput,
        title: str,
        snippet: str,
        result_domain: str,
    ) -> float:
        expected_tokens = self._company_tokens(company.name)

        result_tokens = self._company_tokens(
            f"{title} {snippet}"
        )

        if not expected_tokens:
            return 0.0

        matched = expected_tokens.intersection(result_tokens)

        token_score = len(matched) / len(expected_tokens)

        if result_domain in self.DIRECTORY_DOMAINS:
            maximum = 0.75
        elif result_domain in self.BLOCKED_DOMAINS:
            maximum = 0.55
        else:
            maximum = 0.95

        if token_score == 1.0:
            return maximum

        if token_score >= 0.75:
            return min(maximum, 0.80)

        if token_score >= 0.5:
            return min(maximum, 0.60)

        return min(maximum, 0.25)

    @staticmethod
    def _company_tokens(
        value: str,
    ) -> set[str]:
        ignored = {
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
            if token not in ignored
        }
