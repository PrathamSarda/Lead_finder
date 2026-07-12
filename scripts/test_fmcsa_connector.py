from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import (
    FMCSAConnector,
)

connector = FMCSAConnector()

companies = connector.search(
    SearchFilters(
        max_results=10,
    )
)

print()

print(f"Qualified Companies: {len(companies)}")

print()

for company in companies:

    print("-" * 60)

    print(company.company_name)

    print(company.location)

    print(company.industry)

    print(company.employee_count)