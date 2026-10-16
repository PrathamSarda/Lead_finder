from automation.enrichment.contact_page_finder import (
    find_contact_pages,
)
from automation.enrichment.email_extractor import extract_emails
from automation.enrichment.phone_extractor import extract_phone_numbers
from automation.enrichment.website_fetcher import fetch_website
from automation.models.enrichment_result import EnrichmentResult


def _merge_unique(
    existing_values: list[str],
    new_values: list[str],
) -> list[str]:
    """
    Merge two lists while removing duplicates.
    """

    merged_values = set(existing_values)
    merged_values.update(new_values)

    return sorted(merged_values)


def enrich_company(
    website: str,
    region: str = "US",
) -> EnrichmentResult:
    """
    Enrich a company website with publicly available contact details.

    The function:
    - fetches the homepage,
    - extracts homepage emails and phone numbers,
    - discovers relevant contact pages,
    - visits those pages,
    - extracts additional contact information,
    - merges and deduplicates all results.

    A failure on one contact page does not stop the entire enrichment.
    """

    result = EnrichmentResult(
        website=website,
    )

    homepage_result = fetch_website(website)

    if not homepage_result.success:
        result.error = homepage_result.error
        return result

    homepage_html = homepage_result.html or ""
    homepage_url = homepage_result.final_url or website

    result.homepage_url = homepage_url
    result.fetched_pages.append(homepage_url)

    result.emails = extract_emails(homepage_html)
    for email in result.emails:
        result.email_sources.setdefault(email, homepage_url)

    result.phone_numbers = extract_phone_numbers(
        homepage_html,
        region=region,
    )
    for phone in result.phone_numbers:
        result.phone_sources.setdefault(phone, homepage_url)

    result.contact_pages = find_contact_pages(
        html=homepage_html,
        base_url=homepage_url,
    )

    for contact_page in result.contact_pages:
        page_result = fetch_website(contact_page)

        if not page_result.success:
            result.failed_pages.append(contact_page)
            continue

        page_html = page_result.html or ""
        
        resolved_page_url = page_result.final_url or contact_page
        result.fetched_pages.append(resolved_page_url)

        page_emails = extract_emails(page_html)
        for email in page_emails:
            result.email_sources.setdefault(email, resolved_page_url)

        page_phone_numbers = extract_phone_numbers(
            page_html,
            region=region,
        )
        for phone in page_phone_numbers:
            result.phone_sources.setdefault(phone, resolved_page_url)

        result.emails = _merge_unique(
            result.emails,
            page_emails,
        )

        result.phone_numbers = _merge_unique(
            result.phone_numbers,
            page_phone_numbers,
        )

    result.fetched_pages = _merge_unique(
        [],
        result.fetched_pages,
    )

    result.failed_pages = _merge_unique(
        [],
        result.failed_pages,
    )

    result.success = True

    return result