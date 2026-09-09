from __future__ import annotations

import re
from urllib.parse import urlparse

from automation.intelligence.extractors.base import BaseExtractor
from automation.intelligence.models import (
    CollectedResult,
    CompanyEvidence,
    CompanyInput,
)
from backend.app.models import company


class GenericExtractor(BaseExtractor):
    """
    Extract structured company evidence from ordinary web search results.

    This extractor acts as the fallback for results that do not belong to
    specialized sources such as LinkedIn, Indeed, Glassdoor, or Clutch.
    """

    EXCLUDED_DOMAINS = {
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

    BLOCKED_DOMAINS = {
    "linkedin.com",
    "zoominfo.com",
    "crunchbase.com",
    "manta.com",
    "buzzfile.com",
    "dandb.com",
    "fyple.com",
    "dotsearch.us",
    "rocketreach.co",
    "signalhire.com",
    "opencorporates.com",
    "yellowpages.com",
    "mapquest.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "glassdoor.com",
    "indeed.com",
    "birdeye.com",
    "newbizbot.ai",
    "osha.gov",
    "fmcsa.dot.gov",
    "myplaniq.com",
"thomasnet.com",
"mckeesrocks.com",
"puc.pa.gov",
    "twitter.com",
    "x.com",

    "zoominfo.com",
    "crunchbase.com",
    "pitchbook.com",
    "apollo.io",

    "birdeye.com",
    "reviews.birdeye.com",

    "dcontrol.com",
    "roserocket.com",
    "logisticsvendorlocator.com",

    "whatsinproducts.com",
    "appsruntheworld.com",
    "newbizbot.ai",

    "safer.fmcsa.dot.gov",
    "osha.gov",
}

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    PHONE_PATTERN = re.compile(
        r"""
        (?:
            \+?1[\s.-]?
        )?
        (?:
            \(\d{3}\)
            |
            \d{3}
        )
        [\s.-]?
        \d{3}
        [\s.-]?
        \d{4}
        """,
        re.VERBOSE,
    )

    @property
    def source_name(self) -> str:
        return "generic"

    @property
    def default_confidence(self) -> float:
        return 0.70

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

        hostname = self._normalize_hostname(parsed.hostname)

        if not hostname:
            return False

        return not self._is_excluded_domain(hostname)

    def extract(
        self,
        company: CompanyInput,
        collected_results: list[CollectedResult],
    ) -> list[CompanyEvidence]:
        evidence: list[CompanyEvidence] = []
        seen_urls: set[str] = set()

        for collected_result in self.supported_results(collected_results):
            search_result = collected_result.result

            canonical_url = self._canonical_url(search_result.url)

            if not canonical_url:
                continue

            if canonical_url in seen_urls:
                continue

            seen_urls.add(canonical_url)

            combined_text = " ".join(
                part
                for part in (
                    search_result.title,
                    search_result.snippet,
                )
                if part
            )

            company_name = self.first_non_empty(
                self._extract_company_name(search_result.title),
                company.name,
            )

            email = self._extract_email(combined_text)
            phone = self._extract_phone(combined_text)
            location = self._extract_location(
                search_result.snippet,
                company,
            )
            website = self._website_from_url(
    search_result.url,
)

            if website and self._is_blocked_domain(website):
                continue

            evidence.append(
    self.build_evidence(
        title=search_result.title,
        url=search_result.url,
        snippet=search_result.snippet,
        company_name=company_name,
        website=self._website_from_url(search_result.url),
        email=email,
        phone=phone,
        location=location,
        confidence=self._calculate_confidence(
            email=email,
            phone=phone,
            company_name=company_name,
            expected_company_name=company.name,
            website=self._website_from_url(search_result.url),
        ),
    )
)
        
        return evidence
 
    def _calculate_confidence(
    self,
    *,
    email: str | None,
    phone: str |None,
    company_name: str | None,
    expected_company_name: str,
    website: str | None,
) -> float:

        confidence = 0.60
        if company_name:
            if (
                self._normalize_company_name(company_name)
                ==
                self._normalize_company_name(expected_company_name)
            ):
                confidence += 0.20

        if email:
            confidence += 0.10

        if phone:
            confidence += 0.05

        if website:

            website = website.lower()

            expected = (
                self._normalize_company_name(expected_company_name)
                .replace(" ", "")
            )

            if expected in website:
                confidence += 0.10

        return min(confidence, 0.95)

    @classmethod
    def _is_excluded_domain(
        cls,
        hostname: str,
    ) -> bool:
        return any(
            hostname == domain
            or hostname.endswith(f".{domain}")
            for domain in cls.EXCLUDED_DOMAINS
        )

    @staticmethod
    def _normalize_hostname(
        hostname: str | None,
    ) -> str:
        if not hostname:
            return ""

        hostname = hostname.lower().strip()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    @classmethod
    def _website_from_url(
        cls,
        url: str,
    ) -> str | None:
        if not url:
            return None

        try:
            parsed = urlparse(url)
        except ValueError:
            return None

        hostname = cls._normalize_hostname(parsed.hostname)

        if not hostname:
            return None

        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            scheme = "https"

        return f"{scheme}://{hostname}"

    @classmethod
    def _canonical_url(
        cls,
        url: str,
    ) -> str:
        if not url:
            return ""

        try:
            parsed = urlparse(url.strip())
        except ValueError:
            return ""

        hostname = cls._normalize_hostname(parsed.hostname)

        if not hostname:
            return ""

        path = parsed.path.rstrip("/")

        return f"{hostname}{path}".lower()

    @classmethod
    def _extract_email(
        cls,
        text: str,
    ) -> str | None:
        if not text:
            return None

        match = cls.EMAIL_PATTERN.search(text)

        if not match:
            return None

        return match.group(0).lower()

    @classmethod
    def _extract_phone(
        cls,
        text: str,
    ) -> str | None:
        if not text:
            return None

        match = cls.PHONE_PATTERN.search(text)

        if not match:
            return None

        phone = " ".join(match.group(0).split())

        return phone.strip(" .,-")

    @staticmethod
    def _extract_company_name(
        title: str,
    ) -> str | None:
        if not title:
            return None

        cleaned_title = " ".join(title.split())

        separators = (
            " | ",
            " - ",
            " — ",
            " – ",
            " :: ",
        )

        for separator in separators:
            if separator in cleaned_title:
                first_part = cleaned_title.split(separator, 1)[0].strip()

                if first_part:
                    return first_part

        return cleaned_title


    @staticmethod
    def _extract_location(
        snippet: str,
        company: CompanyInput,
    ) -> str | None:
        fallback_location = ", ".join(
            part
            for part in (
                company.city,
                company.state,
            )
            if part
        )

        if not snippet:
            return fallback_location or None

        location_pattern = re.compile(
            r"""
            \b
            (
                [A-Z][A-Za-z.'-]*
                (?:
                    \s+
                    [A-Z][A-Za-z.'-]*
                )*
            )
            ,\s*
            ([A-Z]{2})
            \b
            """,
            re.VERBOSE,
        )

        matches = list(location_pattern.finditer(snippet))

        if matches:
            # The last valid city/state expression is usually the location,
            # rather than an earlier capitalized phrase in the sentence.
            match = matches[-1]

            city = " ".join(match.group(1).split())
            state = match.group(2)

            return f"{city}, {state}"

        return fallback_location or None
    
    @staticmethod
    def _normalize_company_name(
        company_name: str,
    ) -> str:
        normalized = company_name.lower()

        normalized = re.sub(
            r"\b(?:inc|incorporated|llc|ltd|limited|corp|corporation|company|co)\b",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalized,
        )

        return " ".join(normalized.split())

    @classmethod
    def _is_blocked_domain(
        cls,
        website: str,
    ) -> bool:

        website = website.lower()

        return any(
            blocked in website
            for blocked in cls.BLOCKED_DOMAINS
        )