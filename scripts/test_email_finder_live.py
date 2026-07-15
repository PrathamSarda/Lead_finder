import csv
import time
from pathlib import Path
from automation.enrichment.email_prioritizer import (
    prioritize_emails,
)
from automation.enrichment.company_enricher import enrich_company


COMPANY_WEBSITES = [
    "https://cherokeeculvert.com/",
    "https://www.biolabinc.com/",
    "https://cwtfarmsinternational.com/",
]

OUTPUT_FILE = Path("outputs/email_finder_test.csv")


def main() -> None:
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    for index, website in enumerate(
        COMPANY_WEBSITES,
        start=1,
    ):
        print("\n" + "=" * 80)
        print(
            f"[{index}/{len(COMPANY_WEBSITES)}] "
            f"Processing: {website}"
        )

        started_at = time.perf_counter()

        result = enrich_company(
            website=website,
            region="US",
        )

        elapsed_seconds = (
            time.perf_counter() - started_at
        )

        emails = result.emails
        phone_numbers = result.phone_numbers
        email_priority = prioritize_emails(
            emails=emails,
            website=result.homepage_url or website,
        )

        print(f"Success: {result.success}")
        print(f"Homepage: {result.homepage_url}")
        print(f"Emails found: {len(emails)}")
        print(
            f"Primary email: "
            f"{email_priority.primary_email}"
        )

        print(
            "Business emails: "
            f"{email_priority.business_emails}"
        )

        print(
            "Personal/free-mail emails: "
            f"{email_priority.personal_emails}"
        )

        print(
            "Rejected emails: "
            f"{email_priority.rejected_emails}"
        )

        for email in emails:
            print(f"  - {email}")

        print(
            f"Phone numbers found: "
            f"{len(phone_numbers)}"
        )

        for phone_number in phone_numbers:
            print(f"  - {phone_number}")

        print(
            f"Contact pages discovered: "
            f"{len(result.contact_pages)}"
        )

        for page in result.contact_pages:
            print(f"  - {page}")

        print(
            f"Pages successfully fetched: "
            f"{len(result.fetched_pages)}"
        )

        print(
            f"Pages that failed: "
            f"{len(result.failed_pages)}"
        )

        if result.error:
            print(f"Error: {result.error}")

        print(
            f"Processing time: "
            f"{elapsed_seconds:.2f} seconds"
        )

        results.append(
            {
                "website": website,
                "success": result.success,
                "homepage_url": (
                    result.homepage_url or ""
                ),
                "emails_found": len(emails),
                "emails": "; ".join(emails),
                "primary_email": (
                    email_priority.primary_email or ""
                ),
                "business_emails": "; ".join(
                    email_priority.business_emails
                ),
                "personal_emails": "; ".join(
                    email_priority.personal_emails
                ),
                "rejected_emails": "; ".join(
                    email_priority.rejected_emails
                ),
                "phones_found": len(phone_numbers),
                "phone_numbers": "; ".join(
                    phone_numbers
                ),
                "contact_pages_found": len(
                    result.contact_pages
                ),
                "contact_pages": "; ".join(
                    result.contact_pages
                ),
                "fetched_pages": len(
                    result.fetched_pages
                ),
                "failed_pages": len(
                    result.failed_pages
                ),
                "error": result.error or "",
                "elapsed_seconds": round(
                    elapsed_seconds,
                    2,
                ),
            }
        )

    # Define standard fieldnames explicitly to ensure the CSV structure is safe 
    # even if `results` is entirely empty due to zero targets processed.
    fieldnames = [
        "website", "success", "homepage_url", "emails_found", "emails",
        "primary_email", "business_emails", "personal_emails", "rejected_emails",
        "phones_found", "phone_numbers", "contact_pages_found", "contact_pages",
        "fetched_pages", "failed_pages", "error", "elapsed_seconds"
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)

    successful_companies = sum(
        1
        for item in results
        if item["success"]
    )

    companies_with_email = sum(
        1
        for item in results
        if item["emails_found"] > 0
    )

    companies_with_phone = sum(
        1
        for item in results
        if item["phones_found"] > 0
    )

    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print(
        f"Websites processed: {len(results)}"
    )
    print(
        f"Successfully processed: "
        f"{successful_companies}"
    )
    print(
        f"Companies with email: "
        f"{companies_with_email}"
    )
    print(
        f"Companies with phone: "
        f"{companies_with_phone}"
    )

    email_success_rate = (
        companies_with_email
        / len(results)
        * 100
        if results else 0.0
    )

    print(
        f"Email success rate: "
        f"{email_success_rate:.1f}%"
    )
    print(
        f"CSV report saved to: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()