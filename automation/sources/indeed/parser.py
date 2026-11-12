"""
Indeed job posting and company page parser.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def parse_job_title(raw_title: str) -> str:
    """Extract standard job title from Indeed raw title string."""
    if not raw_title:
        return ""
    cleaned = re.sub(r"\s*-\s*Indeed(\.com)?.*$", "", raw_title, flags=re.I).strip()
    cleaned = re.sub(r"\s*\|\s*Indeed(\.com)?.*$", "", cleaned, flags=re.I).strip()
    parts = [p.strip() for p in re.split(r"\s*[-–—|]\s*", cleaned) if p.strip()]
    return parts[0] if parts else cleaned


def parse_company_name_from_url(url: str) -> str | None:
    """Extract company slug or name from an Indeed company URL (e.g. indeed.com/cmp/acme-corp)."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path.startswith("cmp/"):
            parts = path.split("/")
            if len(parts) >= 2:
                slug = parts[1]
                return slug.replace("-", " ").title()
    except Exception:
        pass
    return None

