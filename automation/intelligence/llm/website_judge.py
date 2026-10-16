
from __future__ import annotations

import json
from typing import Literal
from urllib.parse import urlparse

from google import genai
from pydantic import BaseModel, Field

from automation.intelligence.models import CompanyEvidence, CompanyInput


WebsiteClassification = Literal[
    "official_website",
    "directory",
    "social_profile",
    "irrelevant",
    "uncertain",
]


class WebsiteCandidateDecision(BaseModel):
    url: str
    classification: WebsiteClassification
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class WebsiteJudgment(BaseModel):
    candidates: list[WebsiteCandidateDecision]


class WebsiteJudge:
    """Classify candidate company websites using Gemini."""

    MODEL = "gemini-3.8-flash"

    BLOCKED_DOMAINS = {
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "zoominfo.com",
        "crunchbase.com",
        "birdeye.com",
        "yelp.com",
        "yellowpages.com",
        "buildzoom.com",
        "2findlocal.com",
        "indeed.com",
        "glassdoor.com",
    }

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Gemini API key is missing.")

        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url.strip())
        if not parsed.scheme:
            url = "https://" + url.strip()
            parsed = urlparse(url)

        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}".rstrip("/")

    @classmethod
    def _is_blocked(cls, url: str) -> bool:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().removeprefix("www.")

        return any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in cls.BLOCKED_DOMAINS
        )

    def judge(
        self,
        company: CompanyInput,
        evidence_list: list[CompanyEvidence],
    ) -> WebsiteJudgment | None:
        candidates = []
        seen_urls = set()

        for item in evidence_list:
            if not item.website:
                continue

            url = item.website.strip()
            normalized = self._normalize_url(url)

            if not normalized.startswith(("http://", "https://")):
                continue
            if self._is_blocked(normalized) or normalized in seen_urls:
                continue

            seen_urls.add(normalized)
            candidates.append({
                "title": item.title,
                "url": url,
                "snippet": item.snippet[:500],
                "source": item.source,
            })

        if not candidates:
            return None

        prompt = f"""
You are classifying candidate websites for a company lead database.

Company name: {company.name}
City: {company.city or "Unknown"}
State: {company.state or "Unknown"}

Classify each candidate URL as exactly one of:
- official_website: the company's own website
- directory: a business listing, directory, or lead-generation site
- social_profile: a social-media or professional profile
- irrelevant: unrelated to the company
- uncertain: insufficient evidence to classify confidently

Use the title, URL, snippet, and company location as evidence.
Do not assume a site is official just because its name is similar.
Only classify a URL as official when the evidence supports that decision.
Return only the supplied candidate URLs. Do not invent URLs.

Candidates:
{json.dumps(candidates, ensure_ascii=False)}
"""

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": WebsiteJudgment,
                    "temperature": 0,
                },
            )

            if response.parsed is not None:
                judgment = WebsiteJudgment.model_validate(response.parsed)
            elif response.text:
                judgment = WebsiteJudgment.model_validate_json(response.text)
            else:
                return None

            # Keep only decisions for URLs that were actually provided.
            allowed_urls = {self._normalize_url(c["url"]) for c in candidates}
            judgment.candidates = [
                decision
                for decision in judgment.candidates
                if self._normalize_url(decision.url) in allowed_urls
                and not self._is_blocked(self._normalize_url(decision.url))
            ]

            return judgment

        except Exception as exc:
            print(f"Gemini website judge failed: {exc}")
            return None