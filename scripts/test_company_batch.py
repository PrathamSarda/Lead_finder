from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
import random

from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import FMCSAConnector
from automation.intelligence.models import CompanyInput
from automation.intelligence.company_service import CompanyService


@dataclass(slots=True)
class TestCompany:
    name: str
    city: str | None = None
    state: str | None = None


OUTPUT_FILE = Path(
    "data/batch_company_results.csv"
)


def safe_value(value: str | None) -> str:
    return value or ""


def load_sample_companies() -> list[TestCompany]:
    try:
        connector = FMCSAConnector()
        leads = connector.search(SearchFilters(max_results=8))
        companies: list[TestCompany] = []
        for lead in leads:
            city, state = None, None
            if lead.location and "," in lead.location:
                city, state = [p.strip() for p in lead.location.split(",", 1)]
            elif lead.location:
                city = lead.location.strip()
            companies.append(TestCompany(name=lead.company_name, city=city, state=state))
        if companies:
            return companies
    except Exception as exc:
        print(f"FMCSA fallback due to: {exc}")

    return [
        TestCompany(name="Cherokee Culvert Company Inc", city="Macon", state="GA"),
        TestCompany(name="BioLab Inc", city="Lawrenceville", state="GA"),
        TestCompany(name="CWT Farms International Inc", city="Gainesville", state="GA"),
        TestCompany(name="Boise Delivery & Transfer Inc", city="Boise", state="ID"),
        TestCompany(name="Brockman Trucking Inc", city="Afton", state="MN"),
    ]


def main() -> None:
    service = CompanyService()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    companies = load_sample_companies()
    rows: list[dict[str, object]] = []

    print("=" * 100)
    print("COMPANY LEAD FINDER — BATCH VALIDATION")
    print("=" * 100)

    total_started = time.perf_counter()

    for index, test_company in enumerate(
        companies,
        start=1,
    ):
        print()
        print(
            f"[{index}/{len(companies)}] "
            f"{test_company.name}"
        )
        print("-" * 100)

        started = time.perf_counter()

        row: dict[str, object] = {
            "input_company": test_company.name,
            "input_city": test_company.city or "",
            "input_state": test_company.state or "",
            "status": "",
            "resolved_company": "",
            "website": "",
            "email": "",
            "phone": "",
            "location": "",
            "sources": "",
            "confidence": "",
            "runtime_seconds": "",
            "error": "",
        }

        try:
            result = service.resolve(
                CompanyInput(
                    name=test_company.name,
                    city=test_company.city,
                    state=test_company.state,
                )
            )

            runtime = round(
                time.perf_counter() - started,
                2,
            )

            row["runtime_seconds"] = runtime

            if result is None:
                row["status"] = "NO_EVIDENCE"

                print("Status     : NO_EVIDENCE")
                print(f"Runtime    : {runtime}s")

            else:
                row["status"] = "RESOLVED"
                row["resolved_company"] = safe_value(
                    result.company_name
                )
                row["website"] = safe_value(
                    result.website
                )
                row["email"] = safe_value(
                    result.email
                )
                row["phone"] = safe_value(
                    result.phone
                )
                row["location"] = safe_value(
                    result.location
                )
                row["sources"] = ", ".join(
                    result.sources or []
                )
                row["confidence"] = result.confidence

                print("Status     : RESOLVED")
                print(
                    "Company    :",
                    result.company_name or "-",
                )
                print(
                    "Website    :",
                    result.website or "-",
                )
                print(
                    "Email      :",
                    result.email or "-",
                )
                print(
                    "Phone      :",
                    result.phone or "-",
                )
                print(
                    "Location   :",
                    result.location or "-",
                )
                print(
                    "Sources    :",
                    ", ".join(result.sources or [])
                    or "-",
                )
                print(
                    "Confidence :",
                    result.confidence,
                )
                print(
                    "Runtime    :",
                    f"{runtime}s",
                )

        except Exception as exc:
            runtime = round(
                time.perf_counter() - started,
                2,
            )

            row["status"] = "ERROR"
            row["runtime_seconds"] = runtime
            row["error"] = str(exc)

            print("Status     : ERROR")
            print("Reason     :", exc)
            print("Runtime    :", f"{runtime}s")

        rows.append(row)

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "input_company",
                "input_city",
                "input_state",
                "status",
                "resolved_company",
                "website",
                "email",
                "phone",
                "location",
                "sources",
                "confidence",
                "runtime_seconds",
                "error",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    total_runtime = round(
        time.perf_counter() - total_started,
        2,
    )

    resolved_count = sum(
        row["status"] == "RESOLVED"
        for row in rows
    )

    email_count = sum(
        bool(row["email"])
        for row in rows
    )

    phone_count = sum(
        bool(row["phone"])
        for row in rows
    )

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(
        f"Companies tested : {len(rows)}"
    )
    print(
        f"Resolved         : {resolved_count}"
    )
    print(
        f"Emails found     : {email_count}"
    )
    print(
        f"Phones found     : {phone_count}"
    )
    print(
        f"Total runtime    : {total_runtime}s"
    )
    print(
        f"CSV output       : {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()