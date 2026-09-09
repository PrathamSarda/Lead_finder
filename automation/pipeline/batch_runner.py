"""
Batch runner: FMCSA companies -> LeadPipeline -> CSV/cache.

Usage:
    python -m automation.pipeline.batch_runner --max-results 100

Every resolved company is written to a JSON cache keyed by normalized
company name. On the next run, cached companies are skipped entirely --
no DDGS call, no Zenserp call, no website fetch. This matters because
the same FMCSA company can otherwise get re-queried across runs while
you're iterating on the pipeline, silently burning paid-provider quota.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

from automation.models.search_filters import SearchFilters
from automation.pipeline.lead_pipeline import LeadPipeline
from automation.sources.fmcsa.connector import FMCSAConnector

logger = logging.getLogger(__name__)

CACHE_PATH = Path("data/lead_cache.json")
OUTPUT_PATH = Path("outputs/leads.csv")


def _normalize_key(company_name: str) -> str:
    return " ".join(company_name.strip().lower().split())


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}

    try:
        return json.loads(CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning(
            "Cache file at %s is unreadable, starting fresh.",
            CACHE_PATH,
        )
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def run(max_results: int = 100) -> None:
    filters = SearchFilters()
    filters.max_results = max_results

    companies = FMCSAConnector().search(filters)
    logger.info("Fetched %d companies from FMCSA.", len(companies))

    cache = _load_cache()
    pipeline = LeadPipeline()

    rows = []
    resolved_from_cache = 0
    resolved_fresh = 0
    failed = 0

    for company in companies:
        key = _normalize_key(company.company_name)

        if key in cache:
            resolved_from_cache += 1
            row = cache[key]
        else:
            result = pipeline.run(
                company_name=company.company_name,
                location=company.location,
            )

            row = {
                "company_name": company.company_name,
                "location": company.location,
                "website": result.website,
                "website_source": result.website_source,
                "emails": result.emails,
                "phones": result.phone_numbers,
                "success": result.success,
                "error": result.error,
            }

            cache[key] = row

            if result.success:
                resolved_fresh += 1
            else:
                failed += 1
                # Do not persist failures into the cache: a failure
                # today (rate limit, transient provider error, a bug
                # that just got fixed) should be retried on the next
                # run, not permanently skipped.
                del cache[key]

        rows.append(row)

    _save_cache(cache)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_name",
                "location",
                "website",
                "website_source",
                "emails",
                "phones",
                "success",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    logger.info(
        "Done. %d from cache, %d resolved fresh, %d failed. Output: %s",
        resolved_from_cache,
        resolved_fresh,
        failed,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=100)
    args = parser.parse_args()

    run(max_results=args.max_results)