from automation.models.search_filters import SearchFilters
from automation.sources.google.search import GoogleSource


def main():
    print("=" * 60)
    print("Lead Discovery Engine")
    print("=" * 60)

    # Default search configuration
    filters = SearchFilters()

    print(f"Country          : {filters.country}")
    print(f"Employee Range   : {filters.employee_range}")
    print(f"Maximum Results  : {filters.max_results}")

    print("\nStarting Google Search...\n")

    google = GoogleSource()

    companies = google.search(filters)

    print(f"\nFound {len(companies)} companies.\n")

    for index, company in enumerate(companies, start=1):
        print("-" * 40)
        print(f"Company : {company.company_name}")
        print(f"Website : {company.website}")
        print(f"Industry: {company.industry}")
        print(f"Location: {company.location}")
        print(f"Employees: {company.employee_count}")
        print(f"Source  : {company.source}")

    print("\nSearch completed successfully!")


if __name__ == "__main__":
    main()
