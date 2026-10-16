import sys
from automation.intelligence.company_service import CompanyService
from automation.intelligence.models import CompanyInput

service = CompanyService()

if len(sys.argv) > 1:
    company_name = sys.argv[1]
    city = sys.argv[2] if len(sys.argv) > 2 else None
    state = sys.argv[3] if len(sys.argv) > 3 else None
else:
    company_name = "Cherokee Culvert Company"
    city = "Macon"
    state = "Georgia"

print(f"Resolving: {company_name} ({city}, {state})")
company = CompanyInput(
    name=company_name,
    city=city,
    state=state,
)

result = service.resolve(company)

print()
print("=" * 80)
print("FINAL RESULT")
print("=" * 80)

if result:
    print("Company   :", result.company_name)
    print("Website   :", result.website)
    print("Email     :", result.email)
    print("Phone     :", result.phone)
    print("Location  :", result.location)
    print("Sources   :", result.sources)
    print("Confidence:", result.confidence)
else:
    print("Company lead could not be resolved.")