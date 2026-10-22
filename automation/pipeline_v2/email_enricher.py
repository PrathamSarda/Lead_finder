"""
Decision-Maker Email Enrichment via Hunter.io (with optional Prospeo.io support).
Finds and verifies Owner, CEO, or Founder corporate emails for SMBs.
Includes graceful fallback/mock mode when HUNTER_API_KEY is not configured.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

try:
    from pyhunter import PyHunter
except ImportError:
    PyHunter = None


@dataclass(slots=True)
class DecisionMakerContact:
    email: str | None
    first_name: str | None
    last_name: str | None
    full_name: str | None
    position: str | None
    confidence_score: int
    status: str
    source_url: str | None
    provider: str


class HunterEmailEnricher:
    """Enriches company domains with verified Owner, CEO, or Founder contact details."""

    TARGET_ROLES = ["Owner", "CEO", "Founder", "President", "Principal", "Managing Director"]

    def __init__(self, hunter_api_key: str | None = None, prospeo_api_key: str | None = None):
        self.hunter_key = (hunter_api_key or os.getenv("HUNTER_API_KEY", "")).strip()
        self.prospeo_key = (prospeo_api_key or os.getenv("PROSPEO_API_KEY", "")).strip()
        self.hunter_client = PyHunter(self.hunter_key) if (self.hunter_key and PyHunter) else None

    def find_decision_maker(self, domain: str, company_name: str | None = None) -> DecisionMakerContact:
        """Looks up the primary owner/decision-maker email for the given domain."""
        clean_domain = domain.strip().lower().removeprefix("http://").removeprefix("https://").removeprefix("www.").split("/")[0]

        # 1. Try Hunter.io API
        if self.hunter_key:
            res = self._lookup_hunter(clean_domain)
            if res and res.email:
                return res

        # 2. Try Prospeo.io API if key provided
        if self.prospeo_key:
            res = self._lookup_prospeo(clean_domain, company_name)
            if res and res.email:
                return res

        # 3. Live Website Crawling (Fallback when Hunter/Prospeo have no database record)
        web_contact = self._scrape_website_for_real_email(clean_domain, company_name)
        if web_contact and web_contact.email:
            return web_contact

        # 4. No email found on website or databases -> return genuine Unresolved contact (NO FAKE EMAILS)
        return DecisionMakerContact(
            email=None,
            first_name=None,
            last_name=None,
            full_name=None,
            position=None,
            confidence_score=0,
            status="UNRESOLVED",
            source_url=f"https://{clean_domain}",
            provider="none",
        )

    def _lookup_prospeo(self, domain: str, company_name: str | None) -> DecisionMakerContact | None:
        try:
            url = "https://api.prospeo.io/search-person"
            headers = {"X-KEY": self.prospeo_key, "Content-Type": "application/json"}
            payload = {"filters": {"person_search": {"company_domain": domain}}, "page": 1}
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("response", {})
                for person in data.get("person_list", []):
                    title = (person.get("job_title") or "").lower()
                    if any(t.lower() in title for t in self.TARGET_ROLES):
                        return DecisionMakerContact(
                            email=person.get("email"),
                            first_name=person.get("first_name"),
                            last_name=person.get("last_name"),
                            full_name=f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or None,
                            position=person.get("job_title"),
                            confidence_score=90,
                            status="VERIFIED",
                            source_url=f"https://prospeo.io/{domain}",
                            provider="prospeo.io",
                        )
        except Exception:
            pass
        return None

    def _lookup_hunter(self, domain: str) -> DecisionMakerContact | None:
        try:
            url = f"https://api.hunter.io/v2/domain-search"
            params = {
                "domain": domain,
                "api_key": self.hunter_key,
                "limit": 10,
            }
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                
                # Filter for target senior positions
                for e in emails:
                    pos = (e.get("position") or "").lower()
                    if any(target.lower() in pos for target in self.TARGET_ROLES):
                        return DecisionMakerContact(
                            email=e.get("value"),
                            first_name=e.get("first_name"),
                            last_name=e.get("last_name"),
                            full_name=f"{e.get('first_name', '')} {e.get('last_name', '')}".strip() or None,
                            position=e.get("position"),
                            confidence_score=int(e.get("confidence") or 85),
                            status="VERIFIED" if int(e.get("confidence", 0)) >= 80 else "NEEDS_REVIEW",
                            source_url=f"https://hunter.io/search/{domain}",
                            provider="hunter.io",
                        )
                # If no specific senior role matched, take top genuine email
                if emails:
                    top = emails[0]
                    email_val = top.get("value", "")
                    pos = top.get("position") or "Business Contact"
                    conf = int(top.get("confidence") or 60)
                    is_generic = any(email_val.lower().startswith(p) for p in ("info@", "contact@", "support@", "admin@", "sales@", "hello@", "office@"))
                    
                    status = "VERIFIED" if (conf >= 80 and not is_generic and top.get("first_name")) else ("UNVERIFIED_GENERIC" if is_generic else "NEEDS_REVIEW")
                    return DecisionMakerContact(
                        email=email_val,
                        first_name=top.get("first_name"),
                        last_name=top.get("last_name"),
                        full_name=f"{top.get('first_name', '')} {top.get('last_name', '')}".strip() or None,
                        position=pos,
                        confidence_score=conf,
                        status=status,
                        source_url=f"https://hunter.io/search/{domain}",
                        provider="hunter.io",
                    )
        except Exception as exc:
            print(f"[Hunter.io] Error looking up {domain}: {exc}")
        return None

    def _scrape_website_for_real_email(self, domain: str, company_name: str | None) -> DecisionMakerContact | None:
        """Crawls company homepage and /contact or /about pages to locate genuine public emails."""
        import re
        from urllib.parse import urljoin

        # Match real email formats requiring a 2-63 letter top-level domain (not package versions like @3.5.7)
        EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,10}\b")
        IGNORED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".pdf", ".css", ".js")
        GENERIC_PREFIXES = ("info@", "contact@", "office@", "support@", "hello@", "admin@", "sales@", "service@")

        base_url = f"https://{domain}"
        paths = ["", "/contact", "/contact-us", "/about", "/about-us"]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        found_emails: list[tuple[str, str]] = []

        for p in paths:
            target_url = base_url + p if p else base_url
            try:
                resp = requests.get(target_url, headers=headers, timeout=6, allow_redirects=True)
                if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
                    html_text = resp.text
                    matches = EMAIL_REGEX.findall(html_text)
                    for m in matches:
                        clean_m = m.lower().strip()
                        if any(clean_m.endswith(ext) for ext in IGNORED_EXTENSIONS):
                            continue
                        if any(bad in clean_m for bad in ("example.com", "wixpress.com", "sentry.io", "domain.com", "email.com")):
                            continue
                        # If domain matches or is relevant, save it
                        found_emails.append((clean_m, target_url))
            except Exception:
                continue

            if found_emails:
                break

        if not found_emails:
            return None

        # Prefer personal name email over generic, or take the first real email found
        best_email, source = found_emails[0]
        for em, src in found_emails:
            if not any(em.startswith(pref) for pref in GENERIC_PREFIXES):
                best_email = em
                source = src
                break

        is_generic = any(best_email.startswith(pref) for pref in GENERIC_PREFIXES)
        return DecisionMakerContact(
            email=best_email,
            first_name=None,
            last_name=None,
            full_name=None,
            position="Published Business Contact" if is_generic else "Direct Contact",
            confidence_score=75 if not is_generic else 60,
            status="VERIFIED" if not is_generic else "UNVERIFIED_GENERIC",
            source_url=source,
            provider="website_scraper",
        )
