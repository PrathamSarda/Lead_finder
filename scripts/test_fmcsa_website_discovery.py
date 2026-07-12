from automation.enrichment.website_discovery import (
    discover_company_website,
)
from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import (
    FMCSAConnector,
)


def main() -> None:
    connector = FMCSAConnector()

    companies = connector.search(
        SearchFilters(
            max_results=5,
        )
    )

    for company in companies:
        print("-" * 60)
        print(f"Company: {company.company_name}")

        result = discover_company_website(
            company.company_name
        )

        if result.success:
            print(f"Website: {result.website}")
        else:
            print("Website: Not found")

        print(
            "Candidates checked: "
            f"{len(result.checked_candidates)}"
        )


if __name__ == "__main__":
    main()