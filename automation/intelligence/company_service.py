from __future__ import annotations

from automation.enrichment.company_enricher import (
    enrich_company,
)
from automation.enrichment.email_prioritizer import (
    prioritize_emails,
)
from automation.intelligence.company_pipeline import (
    CompanyPipeline,
)
from automation.intelligence.models import (
    CompanyInput,
)


from automation.resolvers.website_resolver import WebsiteResolver
from automation.intelligence.models import CompanyEvidence


class CompanyService:

    def __init__(self):
        self.resolver = WebsiteResolver()
        self.pipeline = CompanyPipeline()

    def resolve(
        self,
        company: CompanyInput,
    ) -> CompanyEvidence | None:
        location_parts = [p for p in (company.city, company.state) if p and p.strip()]
        location_str = ", ".join(location_parts) if location_parts else None

        # 1. Primary: Use WebsiteResolver (fast, scores candidates, validates homepage HTML)
        website = None
        sources = []
        confidence = 0.70

        try:
            res_result = self.resolver.resolve(
                company_name=company.name,
                location=location_str,
            )
            if res_result and res_result.found and res_result.website:
                website = res_result.website
                sources.append(res_result.provider or "resolver")
                confidence = 0.90 if res_result.validated else 0.75
        except Exception as exc:
            print(f"WebsiteResolver warning: {exc}")

        # 2. Secondary fallback: Use intelligence pipeline if resolver produced no website
        if not website:
            merged = self.pipeline.run(company)
            if merged is not None:
                website = merged.website
                sources.extend(merged.sources or [])
                confidence = max(confidence, merged.confidence)

        if not website:
            print(f"No website could be resolved for {company.name}.")
            return None

        print(f"\nResolved Website: {website}")

        # 3. Enrich the resolved company website (homepage + contact pages)
        enrichment = enrich_company(website)

        print("\nEnrichment Result")
        print("-" * 80)
        print("Homepage:", enrichment.homepage_url)
        print("Contact Pages:", len(enrichment.contact_pages))
        for page in enrichment.contact_pages:
            print(" ", page)
        print("Emails:", enrichment.emails)
        print("Phones:", enrichment.phone_numbers)

        email = None
        email_source_url = None
        if enrichment.emails:
            priority = prioritize_emails(
                emails=enrichment.emails,
                website=website,
            )
            email = priority.primary_email or (enrichment.emails[0] if enrichment.emails else None)
            if email:
                email_source_url = enrichment.email_sources.get(email) or enrichment.homepage_url or website
                sources.append("enrichment")
                confidence = min(1.0, confidence + 0.10)

        phone = (
            enrichment.phone_numbers[0]
            if enrichment.phone_numbers
            else None
        )
        phone_source_url = None
        if phone:
            phone_source_url = enrichment.phone_sources.get(phone) or enrichment.homepage_url or website
            confidence = min(1.0, confidence + 0.05)

        website_source_url = website
        if res_result and res_result.search_result and res_result.search_result.url:
            website_source_url = res_result.search_result.url

        return CompanyEvidence(
            source=sources[0] if sources else "web",
            title=company.name,
            url=website,
            snippet=None,
            company_name=company.name,
            website=website,
            email=email,
            phone=phone,
            location=location_str,
            confidence=round(confidence, 2),
            sources=list(dict.fromkeys(sources)),
            website_source_url=website_source_url,
            email_source_url=email_source_url,
            phone_source_url=phone_source_url,
        )