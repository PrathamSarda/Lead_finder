import csv
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from automation.enrichment.company_enricher import enrich_company
from automation.enrichment.email_prioritizer import prioritize_emails
from automation.models.search_filters import SearchFilters
from automation.resolvers.ddgs_resolver import DDGSWebsiteResolver
from automation.sources.fmcsa.connector import FMCSAConnector


DEFAULT_COMPANY_LIMIT = 10
DEFAULT_DELAY_SECONDS = 2.0

BENCHMARK_DIRECTORY = Path("outputs/benchmark")
RESULTS_FILE = BENCHMARK_DIRECTORY / "benchmark_100.csv"
SUMMARY_FILE = BENCHMARK_DIRECTORY / "benchmark_summary.json"
STATS_FILE = BENCHMARK_DIRECTORY / "benchmark_stats.txt"


@dataclass
class BenchmarkRow:
    """
    Result produced for one FMCSA company.
    """

    company_name: str
    location: str
    industry: str
    employee_count: str
    source: str

    website_found: bool
    website: str
    resolver_provider: str
    resolver_candidates_checked: int
    resolver_error: str

    enrichment_success: bool
    contact_pages_found: int
    contact_pages: str
    emails_found: int
    all_emails: str
    primary_email: str
    business_emails: str
    personal_emails: str
    rejected_emails: str
    phones_found: int
    phone_numbers: str
    fetched_pages: int
    failed_pages: int

    final_status: str
    error: str
    elapsed_seconds: float


def _read_completed_companies(
    results_file: Path,
) -> set[str]:
    """
    Read companies already processed in an earlier partial run.
    """

    if not results_file.exists():
        return set()

    completed_companies = set()

    with results_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            company_name = row.get(
                "company_name",
                "",
            ).strip()

            if company_name:
                completed_companies.add(
                    company_name.casefold()
                )

    return completed_companies


def _append_result(
    row: BenchmarkRow,
    results_file: Path,
) -> None:
    """
    Append one completed company immediately.

    This preserves progress if the benchmark stops unexpectedly.
    """

    result_data = asdict(row)
    file_exists = results_file.exists()

    with results_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=result_data.keys(),
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result_data)


def _classify_status(
    website_found: bool,
    enrichment_success: bool,
    primary_email: Optional[str],
    phones_found: int,
) -> str:
    """
    Assign a clear final benchmark status.
    """

    if not website_found:
        return "no_website_found"

    if not enrichment_success:
        return "website_fetch_failed"

    if primary_email:
        return "email_found"

    if phones_found > 0:
        return "phone_only"

    return "no_contact_details"


def _load_results(
    results_file: Path,
) -> list[dict[str, str]]:
    """
    Load all benchmark results from CSV.
    """

    if not results_file.exists():
        return []

    with results_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        return list(csv.DictReader(csv_file))


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _generate_summary(
    results: list[dict[str, str]],
) -> dict:
    """
    Calculate final benchmark statistics.
    """

    total_companies = len(results)

    websites_found = sum(
        row.get("website_found") == "True"
        for row in results
    )

    enrichment_successes = sum(
        row.get("enrichment_success") == "True"
        for row in results
    )

    companies_with_email = sum(
        bool(row.get("primary_email", "").strip())
        for row in results
    )

    companies_with_phone = sum(
        _safe_int(row.get("phones_found", "0")) > 0
        for row in results
    )

    companies_with_contact_pages = sum(
        _safe_int(
            row.get("contact_pages_found", "0")
        ) > 0
        for row in results
    )

    total_runtime = sum(
        _safe_float(
            row.get("elapsed_seconds", "0")
        )
        for row in results
    )

    status_counts = Counter(
        row.get("final_status", "unknown")
        for row in results
    )

    def percentage(
        value: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0

        return round(
            value / denominator * 100,
            2,
        )

    return {
        "companies_processed": total_companies,
        "websites_found": websites_found,
        "website_success_rate_percent": percentage(
            websites_found,
            total_companies,
        ),
        "websites_successfully_enriched": (
            enrichment_successes
        ),
        "companies_with_contact_pages": (
            companies_with_contact_pages
        ),
        "companies_with_primary_email": (
            companies_with_email
        ),
        "email_success_rate_all_companies_percent": (
            percentage(
                companies_with_email,
                total_companies,
            )
        ),
        "email_success_rate_resolved_websites_percent": (
            percentage(
                companies_with_email,
                websites_found,
            )
        ),
        "companies_with_phone": companies_with_phone,
        "phone_success_rate_all_companies_percent": (
            percentage(
                companies_with_phone,
                total_companies,
            )
        ),
        "status_counts": dict(status_counts),
        "total_processing_seconds": round(
            total_runtime,
            2,
        ),
        "average_seconds_per_company": round(
            total_runtime / total_companies,
            2,
        )
        if total_companies
        else 0.0,
    }


def _write_summary(
    summary: dict,
) -> None:
    """
    Save the summary as JSON and readable text.
    """

    with SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as json_file:
        json.dump(
            summary,
            json_file,
            indent=2,
        )

    lines = [
        "=" * 65,
        "FMCSA LEAD PIPELINE BENCHMARK",
        "=" * 65,
        "",
        (
            "Companies processed: "
            f"{summary['companies_processed']}"
        ),
        (
            "Websites found: "
            f"{summary['websites_found']} "
            f"({summary['website_success_rate_percent']}%)"
        ),
        (
            "Websites successfully enriched: "
            f"{summary['websites_successfully_enriched']}"
        ),
        (
            "Companies with contact pages: "
            f"{summary['companies_with_contact_pages']}"
        ),
        (
            "Companies with primary email: "
            f"{summary['companies_with_primary_email']} "
            f"({summary['email_success_rate_all_companies_percent']}% "
            "of all companies)"
        ),
        (
            "Email rate from resolved websites: "
            f"{summary['email_success_rate_resolved_websites_percent']}%"
        ),
        (
            "Companies with phone: "
            f"{summary['companies_with_phone']} "
            f"({summary['phone_success_rate_all_companies_percent']}%)"
        ),
        (
            "Average time per company: "
            f"{summary['average_seconds_per_company']} seconds"
        ),
        (
            "Total processing time: "
            f"{summary['total_processing_seconds']} seconds"
        ),
        "",
        "Final status counts:",
    ]

    for status, count in sorted(
        summary["status_counts"].items()
    ):
        lines.append(
            f"  {status}: {count}"
        )

    lines.append("=" * 65)

    STATS_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("\n" + "\n".join(lines))


def run_fmcsa_benchmark(
    company_limit: int = DEFAULT_COMPANY_LIMIT,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> dict:
    """
    Run the FMCSA website and email benchmark.

    Existing CSV rows are skipped, allowing interrupted runs
    to continue from the previous checkpoint.
    """

    if company_limit < 1:
        raise ValueError(
            "Company limit must be at least 1."
        )

    if delay_seconds < 0:
        raise ValueError(
            "Delay cannot be negative."
        )

    BENCHMARK_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    completed_companies = _read_completed_companies(
        RESULTS_FILE
    )

    connector = FMCSAConnector()

    resolver = DDGSWebsiteResolver(
        max_results=10,
        validation_limit=5,
    )

    companies = connector.search(
        SearchFilters(
            max_results=company_limit,
        )
    )

    print(
        f"\nQualified FMCSA companies loaded: "
        f"{len(companies)}"
    )
    print(
        f"Previously completed companies: "
        f"{len(completed_companies)}"
    )

    for index, company in enumerate(
        companies,
        start=1,
    ):
        company_key = (
            company.company_name.casefold()
        )

        if company_key in completed_companies:
            print(
                f"[{index}/{len(companies)}] "
                f"Skipping completed company: "
                f"{company.company_name}"
            )
            continue

        print("\n" + "=" * 80)
        print(
            f"[{index}/{len(companies)}] "
            f"{company.company_name}"
        )
        print(f"Location: {company.location}")

        started_at = time.perf_counter()

        website_found = False
        website = ""
        resolver_provider = ""
        resolver_candidates_checked = 0
        resolver_error = ""

        enrichment_success = False
        contact_pages_found = 0
        contact_pages = ""
        emails_found = 0
        all_emails = ""
        primary_email = ""
        business_emails = ""
        personal_emails = ""
        rejected_emails = ""
        phones_found = 0
        phone_numbers = ""
        fetched_pages = 0
        failed_pages = 0
        error = ""

        try:
            resolution = resolver.resolve(
                company_name=company.company_name,
                location=company.location,
            )

            website_found = resolution.success
            website = resolution.website or ""
            resolver_provider = (
                resolution.provider or ""
            )
            resolver_candidates_checked = len(
                resolution.checked_candidates
            )
            resolver_error = resolution.error or ""

            if website_found and website:
                enrichment = enrich_company(
                    website=website,
                    region="US",
                )

                enrichment_success = (
                    enrichment.success
                )

                contact_pages_found = len(
                    enrichment.contact_pages
                )
                contact_pages = "; ".join(
                    enrichment.contact_pages
                )

                emails_found = len(
                    enrichment.emails
                )
                all_emails = "; ".join(
                    enrichment.emails
                )

                phones_found = len(
                    enrichment.phone_numbers
                )
                phone_numbers = "; ".join(
                    enrichment.phone_numbers
                )

                fetched_pages = len(
                    enrichment.fetched_pages
                )
                failed_pages = len(
                    enrichment.failed_pages
                )

                if enrichment.error:
                    error = enrichment.error

                priority = prioritize_emails(
                    emails=enrichment.emails,
                    website=(
                        enrichment.homepage_url
                        or website
                    ),
                )

                primary_email = (
                    priority.primary_email or ""
                )
                business_emails = "; ".join(
                    priority.business_emails
                )
                personal_emails = "; ".join(
                    priority.personal_emails
                )
                rejected_emails = "; ".join(
                    priority.rejected_emails
                )

        except Exception as exc:
            error = (
                f"{type(exc).__name__}: {exc}"
            )

        elapsed_seconds = (
            time.perf_counter() - started_at
        )

        final_status = _classify_status(
            website_found=website_found,
            enrichment_success=enrichment_success,
            primary_email=primary_email or None,
            phones_found=phones_found,
        )

        row = BenchmarkRow(
            company_name=company.company_name,
            location=company.location or "",
            industry=company.industry or "",
            employee_count=(
                company.employee_count or ""
            ),
            source=company.source or "FMCSA",
            website_found=website_found,
            website=website,
            resolver_provider=resolver_provider,
            resolver_candidates_checked=(
                resolver_candidates_checked
            ),
            resolver_error=resolver_error,
            enrichment_success=enrichment_success,
            contact_pages_found=(
                contact_pages_found
            ),
            contact_pages=contact_pages,
            emails_found=emails_found,
            all_emails=all_emails,
            primary_email=primary_email,
            business_emails=business_emails,
            personal_emails=personal_emails,
            rejected_emails=rejected_emails,
            phones_found=phones_found,
            phone_numbers=phone_numbers,
            fetched_pages=fetched_pages,
            failed_pages=failed_pages,
            final_status=final_status,
            error=error,
            elapsed_seconds=round(
                elapsed_seconds,
                2,
            ),
        )

        _append_result(
            row=row,
            results_file=RESULTS_FILE,
        )

        print(f"Website: {website or 'Not found'}")
        print(
            f"Primary email: "
            f"{primary_email or 'Not found'}"
        )
        print(f"Phones found: {phones_found}")
        print(f"Status: {final_status}")
        print(
            f"Time: {elapsed_seconds:.2f} seconds"
        )

        if resolver_error:
            print(
                f"Resolver message: "
                f"{resolver_error}"
            )

        if error:
            print(f"Error: {error}")

        completed_companies.add(company_key)

        if delay_seconds:
            time.sleep(delay_seconds)

    results = _load_results(
        RESULTS_FILE
    )

    summary = _generate_summary(results)

    _write_summary(summary)

    return summary