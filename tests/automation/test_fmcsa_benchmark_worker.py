from automation.workers.fmcsa_benchmark_worker import (
    _classify_status,
    _generate_summary,
)


def test_status_is_no_website_when_resolution_fails():
    assert _classify_status(
        website_found=False,
        enrichment_success=False,
        primary_email=None,
        phones_found=0,
    ) == "no_website_found"


def test_status_is_email_found_when_email_exists():
    assert _classify_status(
        website_found=True,
        enrichment_success=True,
        primary_email="info@example.com",
        phones_found=1,
    ) == "email_found"


def test_status_is_phone_only_without_email():
    assert _classify_status(
        website_found=True,
        enrichment_success=True,
        primary_email=None,
        phones_found=1,
    ) == "phone_only"


def test_generate_summary_calculates_rates():
    results = [
        {
            "website_found": "True",
            "enrichment_success": "True",
            "primary_email": "info@example.com",
            "phones_found": "1",
            "contact_pages_found": "1",
            "final_status": "email_found",
            "elapsed_seconds": "2.5",
        },
        {
            "website_found": "False",
            "enrichment_success": "False",
            "primary_email": "",
            "phones_found": "0",
            "contact_pages_found": "0",
            "final_status": "no_website_found",
            "elapsed_seconds": "1.5",
        },
    ]

    summary = _generate_summary(results)

    assert summary["companies_processed"] == 2
    assert summary["websites_found"] == 1
    assert (
        summary[
            "website_success_rate_percent"
        ]
        == 50.0
    )
    assert (
        summary[
            "companies_with_primary_email"
        ]
        == 1
    )
    assert (
        summary[
            "email_success_rate_all_companies_percent"
        ]
        == 50.0
    )