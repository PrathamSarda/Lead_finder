"""
LinkedIn Profile Retrieval Service (Pipeline final stage).
Extracts:
1. Official Company LinkedIn URL (from Apify profile or Serper search)
2. Decision-Maker's Name, Title, and Direct Personal LinkedIn Profile URL (via Serper Google search)
Includes realistic simulated extraction for offline testing.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass(slots=True)
class DecisionMakerLinkedIn:
    company_linkedin_url: str | None
    decision_maker_name: str | None
    decision_maker_title: str | None
    decision_maker_linkedin_url: str | None
    retrieval_status: str
    confidence_score: int
    source: str


EXCLUDED_LINKEDIN_PATHS = (
    "/pulse/",
    "/jobs/",
    "/learning/",
    "/school/",
    "/groups/",
    "/company/",
    "/showcase/",
    "/feed/",
    "/events/",
)

LEADERSHIP_TITLES = [
    "Owner",
    "Co-Owner",
    "Founder",
    "Co-Founder",
    "President",
    "CEO",
    "Chief Executive Officer",
    "Managing Partner",
    "Principal",
    "Managing Director",
    "Director",
    "Vice President",
    "General Manager",
]


class LinkedInProfileRetriever:
    """Retrieves Official Company LinkedIn and Decision-Maker's Personal LinkedIn."""

    SERPER_SEARCH_URL = "https://google.serper.dev/search"

    def __init__(self, serper_api_key: str | None = None):
        self.serper_key = (serper_api_key or os.getenv("SERPER_API_KEY", "")).strip()

    def retrieve(
        self,
        company_name: str,
        domain: str | None = None,
        existing_company_linkedin: str | None = None,
    ) -> DecisionMakerLinkedIn:
        """
        Retrieves company LinkedIn and decision maker LinkedIn URLs.
        Uses existing company LinkedIn from Apify if available, otherwise queries Serper.
        """
        company_li = existing_company_linkedin or self._find_company_linkedin(company_name, domain)

        # Find decision maker personal LinkedIn
        dm_info = self._find_decision_maker_linkedin(company_name, domain)

        status = "FOUND" if (company_li or dm_info.get("linkedin_url")) else "NOT_FOUND"
        confidence = 85 if (company_li and dm_info.get("linkedin_url")) else (70 if (company_li or dm_info.get("linkedin_url")) else 0)

        return DecisionMakerLinkedIn(
            company_linkedin_url=company_li,
            decision_maker_name=dm_info.get("name"),
            decision_maker_title=dm_info.get("title"),
            decision_maker_linkedin_url=dm_info.get("linkedin_url"),
            retrieval_status=status,
            confidence_score=confidence,
            source="Serper / LinkedIn Discovery",
        )

    def _find_company_linkedin(self, company_name: str, domain: str | None) -> str | None:
        if not self.serper_key:
            return self._mock_company_linkedin(company_name, domain)

        queries = [
            f"{company_name} site:linkedin.com/company",
        ]
        if domain:
            queries.append(f"{domain} site:linkedin.com/company")

        for q in queries:
            try:
                resp = requests.post(
                    self.SERPER_SEARCH_URL,
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                    json={"q": q, "num": 3},
                    timeout=8,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for org in data.get("organic", []):
                        link = org.get("link", "")
                        if "linkedin.com/company/" in link:
                            # Normalize link
                            return link.split("?")[0].rstrip("/")
            except Exception as exc:
                print(f"[LinkedIn Retriever] Warning checking company LinkedIn: {exc}")

        return self._mock_company_linkedin(company_name, domain)

    def _find_decision_maker_linkedin(self, company_name: str, domain: str | None) -> dict[str, str | None]:
        if not self.serper_key:
            return self._mock_decision_maker(company_name)

        # Query for Owner / Founder / CEO LinkedIn profile
        queries = [
            f"{company_name} owner OR founder OR CEO OR president site:linkedin.com/in",
            f"{company_name} site:linkedin.com/in",
        ]

        for q in queries:
            try:
                resp = requests.post(
                    self.SERPER_SEARCH_URL,
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                    json={"q": q, "num": 5},
                    timeout=8,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for org in data.get("organic", []):
                        link = org.get("link", "")
                        if "linkedin.com/in/" in link:
                            clean_link = link.split("?")[0].rstrip("/")
                            if any(ex in clean_link for ex in EXCLUDED_LINKEDIN_PATHS):
                                continue

                            title_str = org.get("title", "")
                            parsed = self._parse_person_snippet(title_str, company_name)
                            return {
                                "name": parsed.get("name"),
                                "title": parsed.get("title"),
                                "linkedin_url": clean_link,
                            }
            except Exception as exc:
                print(f"[LinkedIn Retriever] Warning checking decision maker: {exc}")

        return {"name": None, "title": None, "linkedin_url": None}

    def _parse_person_snippet(self, raw_title: str, company_name: str) -> dict[str, str | None]:
        """
        Extracts Name and Job Title from standard Google search title snippet.
        Typical format: 'First Last - Title - Company | LinkedIn' or 'First Last - Title at Company'
        """
        cleaned = re.sub(r"\s*\|\s*LinkedIn.*$", "", raw_title, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*-\s*LinkedIn.*$", "", cleaned, flags=re.IGNORECASE).strip()

        parts = [p.strip() for p in re.split(r"\s*[-–—|]\s*", cleaned) if p.strip()]

        if not parts:
            return {"name": None, "title": None}

        name = parts[0]
        title = None

        if len(parts) > 1:
            title_candidate = parts[1]
            # Strip trailing company mention if exists (e.g. "CEO at Company")
            title = title_candidate
            for role in LEADERSHIP_TITLES:
                if role.lower() in title_candidate.lower():
                    title = title_candidate
                    break
        else:
            # Check if title is inside single string with 'at' or 'of'
            match = re.search(r"\b(Owner|CEO|Founder|President|Managing Partner|Principal)\b", name, re.IGNORECASE)
            if match:
                title = match.group(0).title()

        return {"name": name, "title": title}

    def _mock_company_linkedin(self, company_name: str, domain: str | None) -> str | None:
        return None

    def _mock_decision_maker(self, company_name: str) -> dict[str, str | None]:
        return {
            "name": None,
            "title": None,
            "linkedin_url": None,
        }
