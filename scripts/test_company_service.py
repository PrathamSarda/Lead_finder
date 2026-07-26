from automation.intelligence.company_service import CompanyService
from automation.intelligence.models import CompanyInput

service = CompanyService()

company = CompanyInput(
    name="BROCKMAN TRUCKING INC",
)

result = service.resolve(company)

print()

print("=" * 80)

print("FINAL RESULT")

print("=" * 80)

print()

print("Company :", result.company_name)

print("Website :", result.website)

print("Email   :", result.email)

print("Phone   :", result.phone)