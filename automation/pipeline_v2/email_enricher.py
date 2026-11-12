"""Find and verify a named decision-maker email with Hunter's API."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests


@dataclass(slots=True)
class HunterEmailResult:
    email: str | None
    status: str
    confidence: int | None = None
    source: str = "Hunter Email Finder + Verifier"


class HunterDecisionMakerEmailFinder:
    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = (api_key or os.getenv("HUNTER_API_KEY", "")).strip()
        self.session = session or requests.Session()

    def find_and_verify(self, name: str, domain: str, linkedin_url: str | None = None) -> HunterEmailResult:
        if not self.api_key:
            return HunterEmailResult(None, "NOT_CONFIGURED")
        parts = name.strip().split()
        if len(parts) < 2 or not domain:
            return HunterEmailResult(None, "MISSING_NAME_OR_DOMAIN")
        params = {"domain": domain, "first_name": parts[0], "last_name": " ".join(parts[1:]), "api_key": self.api_key}
        if linkedin_url:
            handle = urlparse(linkedin_url).path.rstrip("/").split("/")[-1]
            if handle:
                params["linkedin_handle"] = handle
        response = self.session.get(
            f"{self.BASE_URL}/email-finder",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        finder_data = response.json().get("data") or {}
        email = finder_data.get("email")
        confidence = finder_data.get("score")
        if not email:
            return HunterEmailResult(None, "NOT_FOUND", confidence)
        normalize = lambda value: re.sub(r"[^a-z]", "", str(value or "").lower())
        requested_first = normalize(parts[0])
        requested_last = normalize(parts[-1])
        returned_first = normalize(finder_data.get("first_name"))
        returned_last = normalize(finder_data.get("last_name"))
        if not returned_first or not returned_last or not returned_first.startswith(requested_first) or not returned_last.startswith(requested_last):
            return HunterEmailResult(None, "PERSON_MISMATCH", confidence)

        # Finder results are checked again through Verifier. A 202 means pending;
        # poll briefly, and treat an unresolved result as unverified.
        for attempt in range(4):
            verification = self.session.get(
                f"{self.BASE_URL}/email-verifier",
                params={"email": email, "api_key": self.api_key},
                timeout=25,
            )
            if verification.status_code == 202 and attempt < 3:
                time.sleep(2)
                continue
            verification.raise_for_status()
            data = (verification.json().get("data") or {})
            status = str(data.get("status") or "unknown").upper()
            score = data.get("score")
            try:
                confidence_score = int(score) if score is not None else confidence
            except (TypeError, ValueError):
                confidence_score = confidence
            return HunterEmailResult(email, status, confidence_score)
        return HunterEmailResult(email, "UNKNOWN", confidence)

    def find_company_email(self, domain: str | None, website: str | None = None) -> HunterEmailResult:
        """
        Find general/official company contact email via website crawling
        and Hunter domain search.
        """
        # 1. Primary: Website Crawl (homepage and /contact)
        if website:
            try:
                from automation.enrichment.website_fetcher import fetch_website
                from automation.enrichment.email_extractor import extract_emails

                urls_to_check = [website]
                clean_web = website.rstrip("/")
                urls_to_check.extend([f"{clean_web}/contact", f"{clean_web}/contact-us", f"{clean_web}/about"])

                generic_prefixes = (
                    "info@", "contact@", "office@", "hello@", "admin@",
                    "support@", "inquiries@", "inquiry@", "team@", "mail@",
                    "accounting@", "billing@", "sales@",
                )

                found_emails: list[str] = []
                for u in urls_to_check:
                    try:
                        fetch = fetch_website(u, timeout=4)
                        if fetch.success and fetch.html:
                            emails = extract_emails(fetch.html)
                            for em in emails:
                                if em not in found_emails:
                                    found_emails.append(em)
                            # If we found an ideal generic corporate email, break early
                            if any(any(em.startswith(pref) for pref in generic_prefixes) for em in found_emails):
                                break
                    except Exception:
                        continue

                if found_emails:
                    # Sort prioritizing generic corporate inbox addresses
                    def _email_rank(email_addr: str) -> int:
                        lower = email_addr.lower()
                        if any(lower.startswith(p) for p in generic_prefixes):
                            return 0
                        if domain and domain.lower() in lower:
                            return 1
                        return 2

                    sorted_emails = sorted(found_emails, key=_email_rank)
                    best_email = sorted_emails[0]
                    return HunterEmailResult(
                        email=best_email,
                        status="VALID",
                        confidence=85,
                        source="Company Website",
                    )
            except Exception as exc:
                print(f"[Email Finder] Website email extraction error: {exc}")

        # 2. Secondary: Hunter Domain Search API
        if self.api_key and domain:
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/domain-search",
                    params={"domain": domain, "api_key": self.api_key, "limit": 10},
                    timeout=15,
                )
                if response.status_code == 200:
                    data = response.json().get("data") or {}
                    emails_list = data.get("emails") or []
                    for item in emails_list:
                        val = item.get("value")
                        item_type = item.get("type", "")
                        if val and (item_type == "generic" or any(val.lower().startswith(p) for p in ("info@", "contact@", "office@", "hello@"))):
                            return HunterEmailResult(
                                email=val,
                                status="VALID",
                                confidence=item.get("confidence", 80),
                                source="Hunter Domain Search",
                            )
                    # Fallback to top email in domain if available
                    if emails_list and emails_list[0].get("value"):
                        top_val = emails_list[0].get("value")
                        return HunterEmailResult(
                            email=top_val,
                            status="VALID",
                            confidence=emails_list[0].get("confidence", 70),
                            source="Hunter Domain Search",
                        )
            except Exception as exc:
                print(f"[Email Finder] Hunter domain-search error: {exc}")

        return HunterEmailResult(email=None, status="NOT_FOUND", confidence=0, source="None")
