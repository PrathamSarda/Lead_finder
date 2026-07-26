from __future__ import annotations

from automation import enrichment
from automation.enrichment.company_enricher import (
    enrich_company,
)
from automation.intelligence.company_pipeline import (
    CompanyPipeline,
)
from automation.intelligence.models import (
    CompanyInput,
)


class CompanyService:

    def __init__(self):

        self.pipeline = CompanyPipeline()


    def resolve(
        self,
        company: CompanyInput,
    ):

        merged = self.pipeline.run(company)
        print()
        print("Merged website:", merged.website)

        if merged is None:
            return None

        if not merged.website:
            return merged

        enrichment = enrich_company(
        merged.website,
        )

        print("\nEnrichment Result")
        print("-" * 80)

        print("Homepage:")
        print(enrichment.homepage_url)

        print()

        print("Contact Pages:")
        for page in enrichment.contact_pages:
            print(" ", page)

        print()

        print("Fetched Pages:")
        for page in enrichment.fetched_pages:
            print(" ", page)

        print()

        print("Emails:")
        print(enrichment.emails)

        print()

        print("Phones:")
        print(enrichment.phone_numbers)
        merged.email = (
            enrichment.emails[0]
            if enrichment.emails
            else None
        )

        merged.phone = (
            enrichment.phone_numbers[0]
            if enrichment.phone_numbers
            else None
        )

        return merged