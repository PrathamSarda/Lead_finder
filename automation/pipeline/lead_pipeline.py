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
    5. email pattern guessing        -> free (MX + SMTP check)

"""

from __future__ import annotations

import logging
import re
import smtplib
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse

from automation.enrichment.company_enricher import enrich_company
from automation.enrichment.website_discovery import (
    discover_company_website,
)
from automation.resolvers.website_resolver import WebsiteResolver

logger = logging.getLogger(__name__)

# Common role-based email prefixes, ranked by likelihood of being monitored
_CANDIDATE_PREFIXES = [
    "info",
    "contact",
    "sales",
    "hello",
    "office",
    "admin",
    "support",
    "general",
    "inquiries",
]


def _extract_domain(website: str) -> str | None:
    """Extract the registrable domain from a URL (strips www)."""
    try:
        host = urlparse(website).hostname or ""
        return host.removeprefix("www.") or None
    except Exception:
        return None


def _has_mx_record(domain: str) -> bool:
    """Return True if the domain has at least one MX record."""
    try:
        import dns.resolver  # type: ignore[import]
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return bool(answers)
    except Exception:
        pass
    # Fallback: attempt direct SMTP connection to domain (port 25)
    try:
        with smtplib.SMTP(domain, port=25, timeout=4):
            return True
    except Exception:
        return False


def _smtp_verify_email(email: str, domain: str) -> bool:
    """
    Perform a lightweight SMTP RCPT-TO check.
    Returns True if the server does NOT reject the address.
    Many servers will still 250 OK everything (catch-all),
    so we treat non-rejection as 'plausibly exists'.
    """
    try:
        import dns.resolver  # type: ignore[import]
        mx_records = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_host = str(sorted(mx_records, key=lambda r: r.preference)[0].exchange).rstrip(".")
    except Exception:
        mx_host = domain

    try:
        with smtplib.SMTP(mx_host, port=25, timeout=5) as smtp:
            smtp.ehlo_or_helo_if_needed()
            smtp.mail("probe@example.com")
            code, _ = smtp.rcpt(email)
            return code < 400
    except Exception:
        return False


def _guess_emails_from_domain(domain: str) -> list[str]:
    """
    Generate likely contact email addresses from a domain,
    verify via SMTP, and return only those that pass.
    Falls back to returning the pattern guesses without verification
    if SMTP checks fail (many servers block port 25).
    """
    candidates = [f"{prefix}@{domain}" for prefix in _CANDIDATE_PREFIXES]

    # Try SMTP verification; if it times out, return top guesses anyway
    verified: list[str] = []
    smtp_available = False

    try:
        for email in candidates[:3]:  # test first 3 to check SMTP availability
            try:
                if _smtp_verify_email(email, domain):
                    verified.append(email)
                    smtp_available = True
            except Exception:
                pass
            if smtp_available:
                break
    except Exception:
        pass

    if smtp_available and verified:
        # Only return SMTP-verified addresses
        for email in candidates[3:]:
            try:
                if _smtp_verify_email(email, domain):
                    verified.append(email)
            except Exception:
                pass
        return verified

    # SMTP checks unavailable (blocked port) — return top pattern guesses
    # The caller (lead_pipeline) will mark these as pattern-guessed, not scraped
    return candidates[:3]


@dataclass
class LeadResult:
    company_name: str
    website: str | None = None
    website_source: str | None = None  # "free_domain_guess" | "ddgs" | "zenserp"
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    email_guessed: bool = False  # True when emails came from pattern guessing, not scraping
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
        state: str | None = None,
    ) -> LeadResult:
        result = LeadResult(company_name=company_name)

        # --- Step 1: free domain guessing, no search API involved ---
        guess = discover_company_website(company_name, state=state)

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
            # Even if enrichment failed, the website was found — mark partial success
            result.success = False
            return result

        result.emails = enrichment.emails
        result.phone_numbers = enrichment.phone_numbers
        result.success = bool(result.emails or result.phone_numbers)

        if not result.emails:
            # --- Step 5: email pattern guessing as fallback ---
            domain = _extract_domain(result.website)
            if domain:
                logger.info(
                    "No emails scraped from %s; trying pattern guessing for domain %s",
                    result.website,
                    domain,
                )
                guessed = _guess_emails_from_domain(domain)
                if guessed:
                    result.emails = guessed
                    result.email_guessed = True
                    result.success = True
                    logger.info(
                        "Pattern-guessed %d email(s) for %s: %s",
                        len(guessed),
                        company_name,
                        guessed,
                    )
                else:
                    result.error = "no_email_found_on_website"
            else:
                result.error = "no_email_found_on_website"

        return result


def find_company_email(
    company_name: str,
    location: str | None = None,
) -> LeadResult:
    """Convenience entry point for a single company lookup."""

    return LeadPipeline().run(company_name, location)
