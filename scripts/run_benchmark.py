import csv
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.intelligence.models import CompanyInput
from automation.intelligence.company_service import CompanyService
from automation.verification.lead_verifier import LeadVerifier

def main():
    service = CompanyService()
    verifier = LeadVerifier()

    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'outputs/leads_20261018_173705.csv'
    companies = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['company_name']
            loc = row['location']
            old_status = row.get('status', 'N/A')
            old_web = row.get('website', 'None')
            city, state = None, None
            if loc and ',' in loc:
                parts = [p.strip() for p in loc.split(',', 1)]
                city, state = parts[0], parts[1]
            elif loc:
                city = loc.strip()
            companies.append((name, city, state, loc, old_status, old_web))

    print(f"Starting benchmark on {len(companies)} companies...\n")
    results = []
    verified_count = 0
    unresolved_count = 0

    for i, (name, city, state, loc) in enumerate(companies, 1):
        print(f"[{i}/{len(companies)}] Processing: {name} ({loc})")
        t0 = time.perf_counter()
        inp = CompanyInput(name=name, city=city, state=state)
        ev = service.resolve(inp)
        dur = round(time.perf_counter() - t0, 2)
        time.sleep(3)  # inter-company delay
        v = verifier.verify(inp, ev, duration=dur)

        status_val = v.status.value if hasattr(v.status, 'value') else str(v.status)
        tier_val = v.lead_tier.value if hasattr(v.lead_tier, 'value') else str(v.lead_tier)

        if status_val == "VERIFIED":
            verified_count += 1
        else:
            unresolved_count += 1

        print(f"   -> Status: {status_val} | Tier: {tier_val} | Web: {ev.website} | ({dur}s)")
        results.append({
            'company': name,
            'location': loc,
            'status': status_val,
            'tier': tier_val,
            'website': ev.website,
            'email': ev.email,
            'phone': ev.phone,
            'duration': dur,
        })

    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPLETED: {verified_count} VERIFIED, {unresolved_count} UNRESOLVED / {len(companies)} total")
    print("=" * 70)
    for r in results:
        print(f"{r['company']:<35} | {r['status']:<12} | {str(r['website']):<35}")

if __name__ == '__main__':
    main()