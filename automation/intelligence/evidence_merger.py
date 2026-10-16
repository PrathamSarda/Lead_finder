from __future__ import annotations

import re
from urllib.parse import urlparse

from automation.intelligence.models import CompanyEvidence


class EvidenceMerger:
    """
    Merge multiple CompanyEvidence objects into one canonical record.
    """

    PLACEHOLDER_EMAIL_PREFIXES = {
        "filler",
        "example",
        "test",
        "testing",
        "dummy",
        "sample",
        "noreply",
        "no-reply",
    }

    BLOCKED_DOMAINS = {
        "zoominfo.com",
        "crunchbase.com",
        "linkedin.com",
        "indeed.com",
        "glassdoor.com",
        "facebook.com",
        "instagram.com",
        "yelp.com",
        "yellowpages.com",
        "mapquest.com",
        "birdeye.com",
        "osha.gov",
        "safer.fmcsa.dot.gov",
        "fmcsa.dot.gov",
        "freightdatawatch.com",
        "allbiz.com",
        "bubba.ai",
        "justia.com",
        "courtlistener.com",
        "telephonedirectories.us",
        "madridportes.es",
        "amazon.com",
        "ganoksin.com",
        "zoom.com",
        "support.zoom.com",
        "findtruckservice.com",
        "carrier411.com",
        "freightconnect.com",
        "freightvet.com",
        "quicktransportsolutions.com",
        "loadwrap.com",
        "usdotlookup.com",
        "thetruckersreport.com",
        "bbb.org",
        "chamberofcommerce.com",
    }

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
            website=self._select_best_website(evidence_list),
            email=self._select_best_email(evidence_list),
            phone=self._select_best_field(
                evidence_list,
                "phone",
            ),
            location=self._select_best_field(
                evidence_list,
                "location",
            ),
            confidence=best.confidence,
        )

        # Fill missing company name from lower-confidence evidence
        if not merged.company_name:
            for item in ordered:
                if item.company_name:
                    merged.company_name = item.company_name
                    break

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

    @staticmethod
    def _select_best_field(
        evidence_list: list[CompanyEvidence],
        field_name: str,
    ) -> str | None:

        candidates = []

        for evidence in evidence_list:
            value = getattr(evidence, field_name, None)

            if not value:
                continue

            value = value.strip()

            if not value:
                continue

            candidates.append(
                (
                    evidence.confidence,
                    value,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]

    @classmethod
    def _select_best_email(
        cls,
        evidence_list: list[CompanyEvidence],
    ) -> str | None:

        candidates = []

        for evidence in evidence_list:
            email = evidence.email

            if not email:
                continue

            email = email.strip().lower()

            if not cls._is_valid_email(email):
                continue

            if cls._is_placeholder_email(email):
                continue

            candidates.append(
                (
                    evidence.confidence,
                    email,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        return bool(
            re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                email,
            )
        )

    @classmethod
    def _is_placeholder_email(
        cls,
        email: str,
    ) -> bool:

        local_part = email.split("@", 1)[0].lower()

        return local_part in cls.PLACEHOLDER_EMAIL_PREFIXES

    @classmethod
    def _select_best_website(
        cls,
        evidence_list: list[CompanyEvidence],
    ) -> str | None:

        website_scores: dict[str, float] = {}

        for evidence in evidence_list:

            if not evidence.website:
                continue

            website = evidence.website.strip().rstrip("/")

            if not website:
                continue

            domain = cls._extract_domain(website)

            if not domain:
                continue

            # Never select known directory / government / social domains
            if cls._is_blocked_domain(domain):
                continue

            from automation.resolvers.domain_similarity import calculate_domain_similarity

            company_name = evidence.company_name or ""
            similarity = calculate_domain_similarity(company_name, website)
            if similarity < 0.30:
                continue

            weighted_score = round(evidence.confidence * (1.0 + similarity), 3)
            website_scores[website.lower()] = (
                website_scores.get(
                    website.lower(),
                    0.0,
                )
                + weighted_score
            )

        if not website_scores:
            return None

        print("\nWebsite scores:")

        for website, score in website_scores.items():
            print(
                f"{website:35} {score}"
            )

        return max(
            website_scores,
            key=website_scores.get,
        )

    @staticmethod
    def _extract_domain(
        website: str,
    ) -> str | None:

        parsed = urlparse(website)

        if parsed.netloc:
            return parsed.netloc.lower()

        # Handle URLs without protocol
        parsed = urlparse(
            f"https://{website}"
        )

        if parsed.netloc:
            return parsed.netloc.lower()

        return None

    @classmethod
    def _is_blocked_domain(
        cls,
        domain: str,
    ) -> bool:

        domain = domain.lower()

        if (
            domain in cls.BLOCKED_DOMAINS
            or any(
                domain.endswith(
                    "." + blocked
                )
                for blocked in cls.BLOCKED_DOMAINS
            )
        ):
            return True

        from automation.verification.directory_registry import (
            is_directory_domain,
            is_civic_or_gov_domain,
            is_foreign_cctld,
        )

        return (
            is_directory_domain(domain)
            or is_civic_or_gov_domain(domain)
            or is_foreign_cctld(domain)
        )