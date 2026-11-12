"""
Indeed company and job discovery connector.

Searches Indeed job listings and company pages for US small businesses,
identifying companies actively hiring for bookkeeping and accounting roles.
"""
from __future__ import annotations

import os
from typing import Any
import requests

from automation.pipeline_v2.indeed_checker import IndeedBookkeepingChecker, IndeedIntentResult


def search(criteria: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Search Indeed for candidate companies or job postings according to criteria.
    Criteria can include:
      - company_name: str
      - niche: str (default: "bookkeeping")
      - location: str
      - limit: int
    """
    company_name = criteria.get("company_name", "")
    domain = criteria.get("domain")
    location = criteria.get("location")
    serper_key = criteria.get("serper_key") or os.getenv("SERPER_API_KEY")

    checker = IndeedBookkeepingChecker(serper_api_key=serper_key)
    res = checker.check_company(company_name, domain=domain, location=location)

    if res.intent_found:
        return [
            {
                "company_name": company_name,
                "domain": domain,
                "location": location,
                "job_title": res.job_title,
                "job_url": res.job_url,
                "intent_found": True,
                "reason": res.reason,
                "source": res.source,
            }
        ]
    return []
