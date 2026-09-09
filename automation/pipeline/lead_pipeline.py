"""
End-to-end lead pipeline: company name -> website -> real email.

This module intentionally replaces `automation/workers/enrichment_worker.py`
(previously a stub) and does NOT use `automation.intelligence.CompanyPipeline`
for email discovery. That pipeline pulls emails out of search-result
snippet text, which is unreliable for small companies. This pipeline
finds a validated website and then scrapes it directly, which is both
more accurate and does not depend on the email appearing in a search
snippet at all.

Cost model, cheapest to most expensive:

    1. generate_domain_candidates()  -> free, no network search
    2. WebsiteResolver (DDGS first)  -> free
    3. WebsiteResolver (Zenserp)     -> paid, only runs if DDGS fails
    4. enrich_company()              -> free (just fetches the site itself)

A paid email-finder API is intentionally NOT called here. Wire one in
at the bottom of `find_company_email()` only if scraping repeatedly
fails for a meaningful fraction of leads -- see the TODO marker below.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from automation.enrichment.company_enricher import enrich_company
from automation.enrichment.website_discovery import (
    discover_company_website,
)
from automation.resolvers.website_resolver import WebsiteResolver

logger = logging.getLogger(__name__)


@dataclass
class LeadResult:
    company_name: str
    website: str | None = None
    website_source: str | None = None  # "free_domain_guess" | "ddgs" | "zenserp"
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    success: bool = False
    error: str | None = None


class LeadPipeline:
    """
    Resolves a company name to a validated website and real contact
    email, spending money only when the free steps fail.
    """

    def __init__(self, resolver: WebsiteResolver | None = None) -> None:
        # WebsiteResolver already defaults to DDGS-first, Zenserp-fallback.
        self.resolver = resolver or WebsiteResolver()

    def run(
        self,
        company_name: str,
        location: str | None = None,
    ) -> LeadResult:
        result = LeadResult(company_name=company_name)

        # --- Step 1: free domain guessing, no search API involved ---
        guess = discover_company_website(company_name)

        if guess.success and guess.website:
            result.website = guess.website
            result.website_source = "free_domain_guess"
        else:
            # --- Step 2/3: DDGS first, Zenserp only as fallback ---
            resolution = self.resolver.resolve(
                company_name=company_name,
                location=location,
            )

            if not resolution.found or not resolution.website:
                result.error = resolution.reason or "website_not_found"
                logger.info(
                    "No website found for %s: %s",
                    company_name,
                    result.error,
                )
                return result

            result.website = resolution.website
            result.website_source = resolution.provider

        # --- Step 4: scrape the real website for a real email ---
        enrichment = enrich_company(result.website)

        if not enrichment.success:
            result.error = enrichment.error or "enrichment_failed"
            return result

        result.emails = enrichment.emails
        result.phone_numbers = enrichment.phone_numbers
        result.success = bool(result.emails)

        if not result.emails:
            # TODO: only if this happens often enough in real usage,
            # add a fallback here:
            #   1. generate info@/sales@/contact@ pattern guesses for
            #      the resolved domain (free)
            #   2. verify via MX + SMTP handshake (free)
            #   3. only then call a paid finder API (Hunter, etc.) as
            #      a last resort for the leads still unresolved
            result.error = "no_email_found_on_website"

        return result


def find_company_email(
    company_name: str,
    location: str | None = None,
) -> LeadResult:
    """Convenience entry point for a single company lookup."""

    return LeadPipeline().run(company_name, location)
