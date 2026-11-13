"""
Indeed Job & Bookkeeping Intent Verification Service.

Checks if a US small business has active or recent job postings on Indeed
indicating that the company requires bookkeeping, accounting, payroll, or tax services.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

import requests


from datetime import date, datetime, timedelta

@dataclass(slots=True)
class IndeedIntentResult:
    intent_found: bool
    job_title: str | None
    job_url: str | None
    reason: str
    source: str = "Indeed Job Postings"
    job_date: str | None = None


INDEED_REGION_CONFIGS: dict[str, dict[str, str]] = {
    "US": {"domain": "indeed.com", "gl": "us"},
    "UK": {"domain": "indeed.co.uk", "gl": "gb"},
    "AU": {"domain": "au.indeed.com", "gl": "au"},
    "CA": {"domain": "ca.indeed.com", "gl": "ca"},
}


def parse_listing_date(raw_date: str | None, snippet: str = "", today: date | None = None) -> date | None:
    """Parse relative or absolute date from Google search result or snippet."""
    today = today or date.today()
    candidate_text = (raw_date or "").strip()
    search_scope = f"{candidate_text} {snippet}".strip()

    if not search_scope:
        return None

    # Handle relative e.g. "3 days ago", "1 week ago", "2 months ago", "11 months ago", "5 hours ago", "30+ days ago"
    rel_match = re.search(r"(\d+)\+?\s*(hour|day|week|month|year)s?\s*ago", search_scope, re.I)
    if rel_match:
        n = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        days = n * {"hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return today - timedelta(days=days)

    # Search for absolute date patterns: "Nov 10, 2023", "November 10, 2023", "10 Nov 2023", "2023-11-10"
    abs_match = re.search(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})\b",
        search_scope,
        re.I,
    )
    if abs_match:
        month_str, day_str, year_str = abs_match.groups()
        for fmt in ("%b %d %Y", "%B %d %Y"):
            try:
                return datetime.strptime(f"{month_str[:3]} {day_str} {year_str}", "%b %d %Y").date()
            except ValueError:
                pass

    # Try common absolute date formats directly
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(candidate_text, fmt).date()
        except ValueError:
            pass

    return None


BOOKKEEPING_ROLE_KEYWORDS = [
    "bookkeeper",
    "bookkeeping",
    "full charge bookkeeper",
    "accountant",
    "accounting",
    "accounting clerk",
    "accounting assistant",
    "accounting specialist",
    "staff accountant",
    "junior accountant",
    "quickbooks",
    "payroll",
    "payroll specialist",
    "payroll clerk",
    "tax preparer",
    "cpa",
    "accounts payable",
    "accounts receivable",
]


def _normalize_str(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


class IndeedBookkeepingChecker:
    """Checks Indeed for active bookkeeping and accounting hiring intent."""

    SERPER_SEARCH_URL = "https://google.serper.dev/search"

    def __init__(self, serper_api_key: str | None = None, gemini_api_key: str | None = None):
        self.serper_key = (serper_api_key or os.getenv("SERPER_API_KEY", "")).strip()
        self.gemini_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def check_company(
        self,
        company_name: str,
        domain: str | None = None,
        location: str | None = None,
        after_date: str | date | None = None,
        region: str = "US",
    ) -> IndeedIntentResult:
        """
        Check if the company has active or recent job listings on Indeed
        for bookkeeping, accounting, payroll, or financial management services.
        Optionally filters for listings posted on or after `after_date`.
        """
        if not company_name or not company_name.strip():
            return IndeedIntentResult(
                intent_found=False,
                job_title=None,
                job_url=None,
                reason="Company name was empty.",
            )

        # Normalize cutoff date
        cutoff_date: date | None = None
        if isinstance(after_date, str) and after_date.strip():
            try:
                cutoff_date = datetime.strptime(after_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass
        elif isinstance(after_date, date):
            cutoff_date = after_date

        clean_company = re.sub(r"\b(llc|inc|corp|corporation|company|co|ltd)\b", "", company_name, flags=re.I).strip()
        
        # Sourcing from Serper Google Search with site:indeed
        results = self._search_indeed_postings(clean_company, domain=domain, location=location, region=region, cutoff_date=cutoff_date)

        for item in results:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            combined_text = f"{title} {snippet}".lower()

            # Verify relevance to this company
            if not self._is_relevant_to_company(clean_company, domain, title, snippet, link):
                continue

            # Check date filter if after_date is specified
            item_date = parse_listing_date(item.get("date"), snippet)
            if cutoff_date and item_date and item_date < cutoff_date:
                # Listing is explicitly older than the requested cutoff date
                continue

            # Check for bookkeeping keywords in title or description
            matched_roles = [kw for kw in BOOKKEEPING_ROLE_KEYWORDS if kw in combined_text]
            if matched_roles:
                extracted_title = self._clean_job_title(title, clean_company)
                matched_str = ", ".join(matched_roles[:3])
                date_str = item_date.isoformat() if item_date else item.get("date")
                date_suffix = f" (posted {date_str})" if date_str else ""
                reason = f"Confirmed bookkeeping requirement via Indeed job posting: '{extracted_title}'{date_suffix} (roles/skills: {matched_str})"
                return IndeedIntentResult(
                    intent_found=True,
                    job_title=extracted_title,
                    job_url=link,
                    reason=reason,
                    source=f"Indeed ({region.upper()}) Job Postings",
                    job_date=date_str,
                )

        reason_date = f" on or after {cutoff_date.isoformat()}" if cutoff_date else ""
        return IndeedIntentResult(
            intent_found=False,
            job_title=None,
            job_url=None,
            reason=f"No active bookkeeping or accounting job postings found on Indeed for this company{reason_date}.",
            source="Indeed Job Postings",
        )

    def _search_indeed_postings(
        self,
        company_name: str,
        domain: str | None = None,
        location: str | None = None,
        region: str = "US",
        cutoff_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Search Indeed for bookkeeping and accounting positions for the given company in the specified region."""
        if not self.serper_key:
            return self._mock_check_if_needed(company_name)

        reg = region.upper() if region else "US"
        reg_cfg = INDEED_REGION_CONFIGS.get(reg, INDEED_REGION_CONFIGS["US"])
        indeed_site = reg_cfg.get("domain", "indeed.com")
        gl = reg_cfg.get("gl", "us")

        queries = [
            f'site:{indeed_site}/cmp "{company_name}" (bookkeeper OR bookkeeping OR accountant OR accounting OR payroll OR quickbooks)',
            f'site:{indeed_site}/viewjob "{company_name}" (bookkeeper OR bookkeeping OR accountant OR payroll OR quickbooks)',
            f'site:{indeed_site} "{company_name}" ("bookkeeper" OR "bookkeeping" OR "accountant" OR "accounting" OR "payroll" OR "quickbooks")',
        ]

        all_items: list[dict[str, Any]] = []
        seen_links: set[str] = set()

        # Build payload with time filtering if cutoff_date is provided
        tbs = None
        if cutoff_date:
            days_diff = (date.today() - cutoff_date).days
            if days_diff <= 7:
                tbs = "qdr:w"
            elif days_diff <= 31:
                tbs = "qdr:m"
            elif days_diff <= 365:
                tbs = "qdr:y"

        for q in queries:
            try:
                payload: dict[str, Any] = {"q": q, "num": 5, "gl": gl}
                if tbs:
                    payload["tbs"] = tbs
                resp = requests.post(
                    self.SERPER_SEARCH_URL,
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for org in data.get("organic", []):
                        link = org.get("link", "")
                        if "indeed." in link and link not in seen_links:
                            seen_links.add(link)
                            all_items.append(org)
                    if all_items:
                        break
            except Exception as exc:
                print(f"[Indeed Checker] Search query error: {exc}")

        return all_items

    def _is_relevant_to_company(
        self,
        company_name: str,
        domain: str | None,
        title: str,
        snippet: str,
        link: str,
    ) -> bool:
        """Ensure the Indeed listing actually refers to the target company."""
        norm_company = _normalize_str(company_name)
        company_words = [w for w in norm_company.split() if len(w) > 2]
        
        norm_text = _normalize_str(f"{title} {snippet} {link}")

        # Direct inclusion
        if norm_company in norm_text:
            return True

        # Check domain token
        if domain:
            dom_name = domain.split(".")[0].lower()
            if len(dom_name) >= 3 and dom_name in norm_text:
                return True

        # Check significant words match
        if company_words:
            matched_words = sum(1 for w in company_words if w in norm_text)
            if matched_words / len(company_words) >= 0.6:
                return True

        return False

    def _clean_job_title(self, raw_title: str, company_name: str) -> str:
        """Extract clean job title from Indeed page title snippet (e.g. 'Bookkeeper - Austin, TX - Indeed.com')."""
        cleaned = re.sub(r"\s*-\s*Indeed(\.com)?.*$", "", raw_title, flags=re.I).strip()
        cleaned = re.sub(r"\s*\|\s*Indeed(\.com)?.*$", "", cleaned, flags=re.I).strip()
        parts = [p.strip() for p in re.split(r"\s*[-–—|]\s*", cleaned) if p.strip()]
        if parts:
            return parts[0]
        return raw_title[:60]

    def _mock_check_if_needed(self, company_name: str) -> list[dict[str, Any]]:
        return []

