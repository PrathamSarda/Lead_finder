from automation.intelligence.company_service import CompanyService
from automation.intelligence.models import CompanyInput

service = CompanyService()

company_name = input(
    "Company Name: "
)

company = CompanyInput(
    name=company_name,
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