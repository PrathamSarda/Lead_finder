"""Real Apify LinkedIn company size and public post enrichment."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

try:
    from apify_client import ApifyClient
except ImportError:  # The API gives a clear runtime error when the dependency is missing.
    ApifyClient = None


@dataclass(slots=True)
class LinkedInCompanyProfile:
    company_name: str
    linkedin_url: str | None
    employee_count: int | None
    employee_range: str | None
    passed_size_gate: bool
    recent_posts: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


class ApifyLinkedInEnricher:
    MIN_EMPLOYEES = 10
    MAX_EMPLOYEES = 15

    def __init__(
        self,
        token: str | None = None,
        company_scraper_actor: str | None = None,
        posts_scraper_actor: str | None = None,
        min_employees: int = 10,
        max_employees: int = 15,
    ):
        self.token = (token or os.getenv("APIFY_API_TOKEN", "")).strip()
        self.company_scraper_actor = company_scraper_actor or os.getenv("APIFY_LINKEDIN_COMPANY_ACTOR", "socialdataapi/linkedin-company-scraper")
        self.posts_scraper_actor = posts_scraper_actor or os.getenv("APIFY_LINKEDIN_POSTS_ACTOR", "atomus/linkedin-company-posts-scraper")
        self.client = ApifyClient(self.token) if self.token and ApifyClient else None
        self.min_employees = min_employees
        self.max_employees = max_employees

    def _run_items(self, actor: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Apify token/client is not configured.")
        run = self.client.actor(actor).call(run_input=run_input)
        if not run:
            raise RuntimeError(f"Apify actor {actor} returned no run.")
        status = run.get("status") if isinstance(run, dict) else None
        if status and status != "SUCCEEDED":
            raise RuntimeError(f"Apify actor {actor} finished with status {status}.")
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else None
        if not dataset_id:
            raise RuntimeError(f"Apify actor {actor} returned no dataset.")
        return list(self.client.dataset(dataset_id).iterate_items())

    @staticmethod
    def _number(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return None

    @classmethod
    def _size(
        cls,
        profile: dict[str, Any],
        min_employees: int | None = None,
        max_employees: int | None = None,
    ) -> tuple[int | None, str | None, bool]:
        min_emp = min_employees if min_employees is not None else cls.MIN_EMPLOYEES
        max_emp = max_employees if max_employees is not None else cls.MAX_EMPLOYEES

        count = cls._number(profile.get("employeeCount") or profile.get("employeesCount") or profile.get("employee_count"))
        size_text = str(profile.get("companySize") or profile.get("employeeRange") or profile.get("size") or "").strip()
        if count is not None:
            return count, size_text or str(count), (min_emp <= count <= max_emp)
        bounds = re.search(r"(\d[\d,]*)\s*(?:-|to|–)\s*(\d[\d,]*)", size_text, re.I)
        if bounds:
            lower, upper = int(bounds.group(1).replace(",", "")), int(bounds.group(2).replace(",", ""))
            if upper < min_emp or lower > max_emp:
                return None, size_text, False
            return None, size_text, True
        plus = re.search(r"(\d[\d,]*)\s*\+", size_text)
        if plus:
            lower = int(plus.group(1).replace(",", ""))
            if lower > max_emp:
                return None, size_text, False
            return None, size_text, True
        return None, size_text or "UNKNOWN", False

    def qualify_and_extract_posts(self, company_name: str, domain: str | None = None, linkedin_url: str | None = None) -> LinkedInCompanyProfile:
        if not linkedin_url:
            return LinkedInCompanyProfile(company_name, None, None, "UNKNOWN", False)
        profiles = self._run_items(self.company_scraper_actor, {"urls": [linkedin_url], "maxRetries": 2})
        if not profiles:
            raise RuntimeError("Apify returned no LinkedIn company profile.")
        profile = profiles[0]
        if profile.get("success") is False or profile.get("status") in {"error", "failed", "not_found"}:
            raise RuntimeError(str(profile.get("error") or profile.get("statusMessage") or "LinkedIn company profile could not be read."))
        employee_count, employee_range, passed = self._size(profile, min_employees=self.min_employees, max_employees=self.max_employees)
        posts: list[str] = []
        if passed:
            items = self._run_items(self.posts_scraper_actor, {"companies": [linkedin_url], "maxPosts": 8, "includeComments": False})
            for item in items[:10]:
                text = item.get("text") or item.get("postText") or item.get("content")
                posted = item.get("datePublished") or item.get("postedAt") or item.get("publishedAt") or item.get("postedAgo")
                if text and str(text).strip():
                    posts.append(f"[Posted: {posted}] {str(text).strip()}" if posted else str(text).strip())
        return LinkedInCompanyProfile(
            company_name=str(profile.get("name") or profile.get("companyName") or company_name),
            linkedin_url=linkedin_url,
            employee_count=employee_count,
            employee_range=employee_range,
            passed_size_gate=passed,
            recent_posts=posts,
            raw_data=profile,
        )
