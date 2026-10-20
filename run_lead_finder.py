"""
Production runner script for Company Lead Finder.

Discovers US companies (1-20 employees/units) via FMCSA, resolves their
official websites, crawls homepages and contact pages for verified emails
and phone numbers, and exports qualified leads to CSV.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import FMCSAConnector
from automation.intelligence.models import CompanyInput
from automation.intelligence.company_service import CompanyService
from automation.verification.lead_verifier import LeadVerifier
from automation.verification.models import EXPORT_FIELDNAMES, VerificationStatus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Company Lead Finder - Automated Lead Discovery and Enrichment",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of qualified company leads to discover (default: 10, target: 80)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/leads_{timestamp}.csv",
        help="Output CSV file path template",
    )
    parser.add_argument(
        "--state",
        type=str,
        default=None,
        help="Optional state filter (e.g. TX, GA, CA)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output.format(timestamp=timestamp))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PROKIZEN GLOBAL LLP - AUTOMATED COMPANY LEAD FINDER")
    print(f"Goal: Discover, enrich, and strictly verify {args.count} US companies")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output File: {output_path}")
    print("=" * 80)

    # 1. Discover companies via FMCSA
    print("\n[Step 1/3] Querying FMCSA database for active small US companies...")
    connector = FMCSAConnector()
    filters = SearchFilters(max_results=args.count)
    
    try:
        leads = connector.search(filters)
        print(f"-> Retrieved {len(leads)} company records from FMCSA.")
    except Exception as exc:
        print(f"-> Error fetching FMCSA records: {exc}")
        return 1

    if not leads:
        print("No companies matched the specified criteria.")
        return 0

    # 2. Enrich leads & apply Lead Verification Layer
    print("\n[Step 2/3] Resolving websites and executing Lead Verification Layer...")
    service = CompanyService()
    verifier = LeadVerifier()
    
    results: list[dict[str, object]] = []
    total_verified = 0
    total_needs_review = 0
    total_unresolved = 0
    total_emails = 0
    total_phones = 0
    start_time = time.perf_counter()

    for idx, lead in enumerate(leads, start=1):
        city, state = None, None
        if lead.location and "," in lead.location:
            parts = [p.strip() for p in lead.location.split(",", 1)]
            city, state = parts[0], parts[1]
        elif lead.location:
            city = lead.location.strip()

        print(f"\n[{idx}/{len(leads)}] Processing: {lead.company_name} ({lead.location or 'US'})")
        comp_start = time.perf_counter()

        company_input = CompanyInput(
            name=lead.company_name,
            city=city,
            state=state,
        )

        # Resolve with strict per-company timeout (45s max) to prevent provider hangs
        evidence = None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(service.resolve, company_input)
                evidence = future.result(timeout=45.0)
        except concurrent.futures.TimeoutError:
            print(f"  [TIMEOUT] Resolution exceeded 45s limit for {company_input.name}. Aborting company.")
        except Exception as exc:
            print(f"  [ERROR] Resolution failed for {company_input.name}: {exc}")

        duration = round(time.perf_counter() - comp_start, 2)

        # Inter-company cooldown: prevents DDGS rate-limit cascading across companies.
        if idx < len(leads):
            time.sleep(2)

        # Apply Lead Verification Layer
        verified = verifier.verify(company_input, evidence, duration=duration)

        if verified.status == VerificationStatus.VERIFIED.value:
            total_verified += 1
            print(f"  [VERIFIED] Website : {verified.website}")
            print(f"             Email   : {verified.email or '(none)'} (source: {verified.email_source or 'n/a'})")
            print(f"             Phone   : {verified.phone or '(none)'} (source: {verified.phone_source or 'n/a'})")
            print(f"             Reason  : {verified.status_reason}")
            print(f"             Score   : {verified.confidence} (took {duration}s)")
        elif verified.status == VerificationStatus.NEEDS_REVIEW.value:
            total_needs_review += 1
            print(f"  [NEEDS_REVIEW] Website : {verified.website or '(none)'}")
            print(f"                 Reason  : {verified.status_reason}")
            print(f"                 Score   : {verified.confidence} (took {duration}s)")
        else:
            total_unresolved += 1
            print(f"  [UNRESOLVED] Reason  : {verified.status_reason} (took {duration}s)")

        if verified.email:
            total_emails += 1
        if verified.phone:
            total_phones += 1

        results.append(verified.to_dict())

    # 3. Write verified outputs to CSV with provenance
    print("\n[Step 3/3] Writing verified lead results and provenance to CSV...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDNAMES)
        writer.writeheader()
        for r in results:
            row = {
                field: r.get(field, "") if r.get(field) is not None else ""
                for field in EXPORT_FIELDNAMES
            }
            writer.writerow(row)

    total_full_leads = sum(1 for r in results if r.get("lead_tier") == "FULL_LEAD")
    total_website_only = sum(1 for r in results if r.get("lead_tier") == "WEBSITE_ONLY")
    total_time = round(time.perf_counter() - start_time, 2)

    print("\n" + "=" * 80)
    print("RUN COMPLETE - LEAD VERIFICATION SUMMARY")
    print(f"Total Companies Processed        : {len(leads)}")
    print(f"VERIFIED Leads (Total)           : {total_verified} ({(total_verified/len(leads))*100:.1f}%)")
    print(f"  - Full Leads (Website + Contact): {total_full_leads} ({(total_full_leads/len(leads))*100:.1f}%)")
    print(f"  - Website-Only Leads            : {total_website_only} ({(total_website_only/len(leads))*100:.1f}%)")
    print(f"NEEDS_REVIEW Leads               : {total_needs_review} ({(total_needs_review/len(leads))*100:.1f}%)")
    print(f"UNRESOLVED Leads                 : {total_unresolved} ({(total_unresolved/len(leads))*100:.1f}%)")
    print(f"Verified Emails Extracted        : {total_emails}")
    print(f"Verified Phones Extracted        : {total_phones}")
    print(f"Total Runtime                    : {total_time}s")
    print(f"Results Saved To                 : {output_path.resolve()}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
