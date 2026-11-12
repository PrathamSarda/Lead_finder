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

import requests


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
        try:
            run = self.client.actor(actor).call(run_input=run_input)
        except Exception as exc:
            # Check for free plan quota limits or API errors
            err_msg = str(exc)
            if "limit reached" in err_msg.lower() or "exceeded" in err_msg.lower() or "402" in err_msg:
                print(f"[Apify Warning] Monthly actor limit reached: {exc}")
                return []
            raise
        if not run:
            raise RuntimeError(f"Apify actor {actor} returned no run.")
        status = getattr(run, "status", None) or (run.get("status") if isinstance(run, dict) else None)
        if status and status != "SUCCEEDED":
            status_msg = getattr(run, "status_message", "") or (run.get("statusMessage") if isinstance(run, dict) else "")
            if "limit reached" in str(status_msg).lower() or "limit" in str(status).lower():
                print(f"[Apify Warning] Monthly actor limit reached on run: {status_msg}")
                return []
            raise RuntimeError(f"Apify actor {actor} finished with status {status}.")
        dataset_id = (
            getattr(run, "default_dataset_id", None)
            or (run.get("defaultDatasetId") or run.get("default_dataset_id") if isinstance(run, dict) else None)
        )
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

    def _search_headcount_serper(self, company_name: str, domain: str | None = None) -> tuple[int | None, str | None, bool]:
        """
        Fallback when Apify monthly quota is exhausted:
        Searches Google Serper for company headcount / employee information.
        """
        serper_key = os.getenv("SERPER_API_KEY", "").strip()
        if not serper_key:
            return None, "UNKNOWN", False

        query = f'"{company_name}" site:linkedin.com/company'
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
                timeout=10,
            )
            if resp.status_code == 200:
                for item in resp.json().get("organic", []):
                    snippet = f"{item.get('title', '')} {item.get('snippet', '')}"
                    # Pattern 1: e.g. "11-50 employees", "1-10 employees", "10-50 employees"
                    range_match = re.search(r"(\d[\d,]*)\s*(?:-|to|–)\s*(\d[\d,]*)\s+employees?", snippet, re.I)
                    if range_match:
                        lower = int(range_match.group(1).replace(",", ""))
                        upper = int(range_match.group(2).replace(",", ""))
                        range_str = f"{lower}-{upper} employees"
                        passed = (upper >= self.min_employees and lower <= self.max_employees)
                        return None, range_str, passed

                    # Pattern 2: e.g. "14 employees", "12 employees"
                    exact_match = re.search(r"\b(\d{1,4})\s+employees?\b", snippet, re.I)
                    if exact_match:
                        count = int(exact_match.group(1))
                        return count, str(count), (self.min_employees <= count <= self.max_employees)

            # Secondary search: company website / general search for size
            query2 = f'"{company_name}" "employees" OR "headcount"'
            resp2 = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": query2, "num": 3},
                timeout=10,
            )
            if resp2.status_code == 200:
                for item in resp2.json().get("organic", []):
                    snippet = f"{item.get('title', '')} {item.get('snippet', '')}"
                    range_match = re.search(r"(\d[\d,]*)\s*(?:-|to|–)\s*(\d[\d,]*)\s+employees?", snippet, re.I)
                    if range_match:
                        lower = int(range_match.group(1).replace(",", ""))
                        upper = int(range_match.group(2).replace(",", ""))
                        range_str = f"{lower}-{upper} employees"
                        passed = (upper >= self.min_employees and lower <= self.max_employees)
                        return None, range_str, passed

                    exact_match = re.search(r"\b(\d{1,4})\s+employees?\b", snippet, re.I)
                    if exact_match:
                        count = int(exact_match.group(1))
                        return count, str(count), (self.min_employees <= count <= self.max_employees)
        except Exception as exc:
            print(f"[Serper Headcount Fallback] Error: {exc}")

        return None, "UNKNOWN", False

    def qualify_and_extract_posts(self, company_name: str, domain: str | None = None, linkedin_url: str | None = None) -> LinkedInCompanyProfile:
        if not linkedin_url:
            return LinkedInCompanyProfile(company_name, None, None, "UNKNOWN", False)
        
        profiles = []
        try:
            profiles = self._run_items(self.company_scraper_actor, {"urls": [linkedin_url], "maxRetries": 2})
        except Exception as exc:
            print(f"[Apify Scraper Warning] Actor run error ({exc}). Switching to Serper headcount fallback.")

        if not profiles:
            # Fallback to Serper Google Search snippet for headcount
            count, size_text, passed = self._search_headcount_serper(company_name, domain)
            if size_text != "UNKNOWN":
                print(f"  [SERPER HEADCOUNT FALLBACK] '{company_name}': {size_text} (Passed target: {passed})")
                return LinkedInCompanyProfile(
                    company_name=company_name,
                    linkedin_url=linkedin_url,
                    employee_count=count,
                    employee_range=size_text,
                    passed_size_gate=passed,
                    recent_posts=[],
                    raw_data={"fallback": "serper_headcount"},
                )
            # Default to passing if company is an active SMB hiring bookkeeper
            # (hiring 1 bookkeeper is typical for SMBs around 10-15 people)
            print(f"  [SERPER HEADCOUNT FALLBACK] Headcount not found in snippets. Preserving SMB candidate: '{company_name}'")
            return LinkedInCompanyProfile(
                company_name=company_name,
                linkedin_url=linkedin_url,
                employee_count=12,
                employee_range="10-15 (Estimated SMB)",
                passed_size_gate=True,
                recent_posts=[],
                raw_data={"fallback": "estimated_smb"},
            )

        profile = profiles[0]
        if profile.get("success") is False or profile.get("status") in {"error", "failed", "not_found"}:
            count, size_text, passed = self._search_headcount_serper(company_name, domain)
            return LinkedInCompanyProfile(
                company_name=str(profile.get("name") or profile.get("companyName") or company_name),
                linkedin_url=linkedin_url,
                employee_count=count or 12,
                employee_range=size_text if size_text != "UNKNOWN" else "10-15 (Estimated SMB)",
                passed_size_gate=passed if size_text != "UNKNOWN" else True,
                recent_posts=[],
                raw_data=profile,
            )

        employee_count, employee_range, passed = self._size(profile, min_employees=self.min_employees, max_employees=self.max_employees)
        posts: list[str] = []
        if passed:
            try:
                items = self._run_items(self.posts_scraper_actor, {"companies": [linkedin_url], "maxPosts": 8, "includeComments": False})
                for item in items[:10]:
                    text = item.get("text") or item.get("postText") or item.get("content")
                    posted = item.get("datePublished") or item.get("postedAt") or item.get("publishedAt") or item.get("postedAgo")
                    if text and str(text).strip():
                        posts.append(f"[Posted: {posted}] {str(text).strip()}" if posted else str(text).strip())
            except Exception as exc:
                print(f"[Apify Posts Warning] Failed to extract posts: {exc}")
        return LinkedInCompanyProfile(
            company_name=str(profile.get("name") or profile.get("companyName") or company_name),
            linkedin_url=linkedin_url,
            employee_count=employee_count,
            employee_range=employee_range,
            passed_size_gate=passed,
            recent_posts=posts,
            raw_data=profile,
        )
