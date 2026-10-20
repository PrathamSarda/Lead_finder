from automation.enrichment.contact_page_finder import (
    find_contact_pages,
)
from automation.enrichment.email_extractor import extract_emails
from automation.enrichment.phone_extractor import extract_phone_numbers
from automation.enrichment.website_fetcher import fetch_website
from automation.models.enrichment_result import EnrichmentResult
from automation.verification.directory_registry import (
    is_directory_domain,
    normalize_domain,
)


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

    # Guard: if the homepage redirect landed us on a completely different root domain
    # (e.g. a parked domain pointing to zip-codes.com), abort enrichment entirely.
    original_root = normalize_domain(website)
    final_root = normalize_domain(homepage_url)
    # Allow www/non-www variants and same-registrable-domain subdomains.
    # Reject if the root labels differ completely (different second-level domain).
    if original_root and final_root and original_root != final_root:
        # Extract SLD (second-level domain) for both
        def _sld(d: str) -> str:
            parts = d.split(".")
            return ".".join(parts[-2:]) if len(parts) >= 2 else d

        orig_sld = _sld(original_root)
        final_sld = _sld(final_root)
        if orig_sld != final_sld:
            result.error = f"Enrichment aborted: website redirected from {original_root} to unrelated domain {final_root}"
            result.success = False
            return result

    # Also guard against redirects to known directory/lookup domains
    if is_directory_domain(final_root):
        result.error = f"Enrichment aborted: website redirected to directory domain {final_root}"
        result.success = False
        return result

    result.emails = extract_emails(homepage_html)
    for email in result.emails:
        result.email_sources.setdefault(email, homepage_url)

    result.phone_numbers = extract_phone_numbers(
        homepage_html,
        region=region,
    )
    for phone in result.phone_numbers:
        result.phone_sources.setdefault(phone, homepage_url)

    found_contact_pages = find_contact_pages(
        html=homepage_html,
        base_url=homepage_url,
    )
    # Deduplicate and cap to avoid slow enrichment on sites with many links
    MAX_CONTACT_PAGES = 3
    result.contact_pages = list(dict.fromkeys(found_contact_pages))[:MAX_CONTACT_PAGES]

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