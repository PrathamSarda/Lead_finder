from __future__ import annotations

from automation.enrichment.company_enricher import (
    enrich_company,
)
from automation.enrichment.email_prioritizer import (
    prioritize_emails,
)
from automation.enrichment.website_discovery import (
    discover_company_website,
)
from automation.intelligence.company_pipeline import (
    CompanyPipeline,
)
from automation.intelligence.models import (
    CompanyInput,
)


from automation.resolvers.website_resolver import WebsiteResolver
from automation.intelligence.models import CompanyEvidence
from automation.verification.directory_registry import normalize_domain

# Common role-based email prefixes to try as fallback
_PATTERN_PREFIXES = ["info", "contact", "sales", "hello", "office", "admin"]


def _guess_pattern_email(domain: str) -> str | None:
    """Return the most likely contact email pattern for a domain."""
    # Just return the most common pattern; SMTP verification adds latency
    # and is blocked on many networks. The verifier will mark it accordingly.
    return f"info@{domain}" if domain else None


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

        # 1. Primary: Try free domain guessing first (fastest, no API cost)
        website = None
        sources = []
        confidence = 0.70
        res_result = None

        try:
            guess = discover_company_website(company.name, state=company.state)
            if guess.success and guess.website:
                website = guess.website
                sources.append("domain_guess")
                confidence = 0.85
        except Exception as exc:
            print(f"Domain guess warning: {exc}")

        # 2. Use WebsiteResolver (DDGS + Zenserp fallback) if domain guess failed
        candidate_results = []
        if not website or "domain_guess" in sources:
            # Also run or prepare resolver candidates so review leads have options
            try:
                res_result = self.resolver.resolve(
                    company_name=company.name,
                    location=location_str,
                )
                if res_result:
                    if res_result.candidate_results:
                        candidate_results.extend(res_result.candidate_results)
                    if not website and res_result.found and res_result.website:
                        website = res_result.website
                        sources.append(res_result.provider or "resolver")
                        confidence = 0.90 if res_result.validated else 0.75
                    elif website and res_result.found and res_result.website:
                        guess_norm = normalize_domain(website)
                        res_norm = normalize_domain(res_result.website)
                        if guess_norm == res_norm:
                            # Search engine independently found and confirmed the same domain
                            sources.append(res_result.provider or "resolver")
                            confidence = 0.95
                        elif res_result.validated:
                            # Search-validated domain takes precedence over an unvalidated domain guess
                            print(f"Upgrading domain guess {website} to search-validated website: {res_result.website}")
                            website = res_result.website
                            sources = [res_result.provider or "resolver"]
                            confidence = 0.90
                    # Corroborate domain guess against top search candidate URLs
                    if website and candidate_results:
                        guess_norm = normalize_domain(website)
                        for cand in candidate_results:
                            cand_url = cand.get("url") or ""
                            if normalize_domain(cand_url) == guess_norm:
                                if "ddgs" not in sources and "resolver" not in sources:
                                    sources.append("ddgs")
                                    confidence = max(confidence, 0.90)
                                break
            except Exception as exc:
                print(f"WebsiteResolver warning: {exc}")

        # 3. Secondary fallback: Only invoke intelligence pipeline if WebsiteResolver was NOT run
        # or if we have high-confidence reasons to believe a profile exists.
        # WebsiteResolver already queries DDGS + Zenserp exhaustively. Running 4 more stages
        # of search queries on an unresolvable company causes severe 429 throttling and hangs.
        if not website and not res_result:
            try:
                merged = self.pipeline.run(company)
                if merged is not None:
                    website = merged.website
                    sources.extend(merged.sources or [])
                    confidence = max(confidence, merged.confidence)
                    if getattr(self.pipeline, "last_candidates", None):
                        for lc in self.pipeline.last_candidates[:3]:
                            candidate_results.append({
                                "title": lc.result.title,
                                "url": getattr(lc.result, "destination", None) or lc.result.url,
                                "snippet": lc.result.snippet or "",
                                "score": "75",
                            })
            except Exception as exc:
                print(f"Pipeline fallback warning: {exc}")

        if not website:
            print(f"No website could be resolved for {company.name}.")
            snippet_email = None
            snippet_email_url = None
            snippet_phone = None
            snippet_phone_url = None

            # Snippet contact mining: Extract direct contacts from official DOT / FMCSA directory snippets
            import re
            for cand in candidate_results:
                snip = cand.get("snippet") or ""
                cur_url = cand.get("url") or ""
                if not snippet_email:
                    m_email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", snip)
                    if m_email:
                        snippet_email = m_email.group(0).lower()
                        snippet_email_url = cur_url
                if not snippet_phone:
                    m_phone = re.search(r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}", snip)
                    if m_phone:
                        snippet_phone = m_phone.group(0)
                        snippet_phone_url = cur_url

            return CompanyEvidence(
                source=sources[0] if sources else "fmcsa",
                title=company.name,
                url="",
                snippet=None,
                company_name=company.name,
                website=None,
                email=snippet_email,
                phone=snippet_phone,
                location=location_str,
                confidence=0.50 if (snippet_email or snippet_phone) else 0.0,
                sources=list(dict.fromkeys(sources + (["directory_snippet"] if (snippet_email or snippet_phone) else []))),
                email_source_url=snippet_email_url,
                phone_source_url=snippet_phone_url,
                candidate_results=candidate_results[:3],
            )

        print(f"\nResolved Website: {website}")

        # 3. Enrich the resolved company website (homepage + contact pages)
        enrichment = enrich_company(website)

        # If enrichment was aborted (e.g., cross-domain redirect guard fired on a
        # domain-guessed website), try falling back to the resolver's validated result.
        if not enrichment.success and "domain_guess" in sources and res_result and res_result.found and res_result.website:
            fallback_website = res_result.website
            if fallback_website != website:
                print(f"Domain-guess enrichment failed ({enrichment.error}); falling back to resolver result: {fallback_website}")
                website = fallback_website
                # Replace domain_guess source with the real resolver source
                sources = [s for s in sources if s != "domain_guess"]
                sources.insert(0, res_result.provider or "resolver")
                enrichment = enrich_company(website)
        # If still failed after fallback (or no fallback available), return without contact
        if not enrichment.success:
            print(f"Enrichment failed: {enrichment.error}")
            # If the website was NEVER validated by WebsiteResolver, and enrichment failed
            # to reach it (e.g. ConnectTimeout, dead host, 404), do not retain it as resolved!
            is_search_validated = bool(
                res_result and res_result.found and res_result.validated and normalize_domain(res_result.website or "") == normalize_domain(website)
            )
            if not is_search_validated:
                print(f"Discarding unvalidated and unreachable website: {website}")
                website = None

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

        # 4. Email pattern fallback: guess info@/contact@ when scraping found nothing
        if not email and website:
            try:
                from urllib.parse import urlparse
                host = (urlparse(website).hostname or "").removeprefix("www.")
                if host:
                    guessed = _guess_pattern_email(host)
                    if guessed:
                        email = guessed
                        email_source_url = website
                        sources.append("pattern_guess")
                        # Pattern-guessed emails lower confidence slightly
                        confidence = min(0.85, confidence)
            except Exception:
                pass

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
            candidate_results=candidate_results[:3],
        )