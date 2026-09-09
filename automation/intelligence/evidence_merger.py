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
            website=self._select_best_website(
            evidence_list,
            ),
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

    @staticmethod
    @staticmethod
    def _select_best_website(
        evidence_list: list[CompanyEvidence],
    ) -> str | None:

        website_scores: dict[str, float] = {}

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
        }

        for evidence in evidence_list:

            if not evidence.website:
                continue

            website = evidence.website.rstrip("/").lower()

            # Remove protocol for domain comparison
            domain = website

            if domain.startswith("https://"):
                domain = domain[8:]

            elif domain.startswith("http://"):
                domain = domain[7:]

            domain = domain.split("/")[0]

            # Never select known directory / government / social domains
            if (
                domain in BLOCKED_DOMAINS
                or any(domain.endswith("." + blocked) for blocked in BLOCKED_DOMAINS)
            ):
                continue

            website_scores[website] = (
                website_scores.get(website, 0.0)
                + evidence.confidence
            )

        if not website_scores:
            return None

        print("\nWebsite scores:")

        for website, score in website_scores.items():
            print(f"{website:35} {score}")

        return max(
            website_scores,
            key=website_scores.get,
        )