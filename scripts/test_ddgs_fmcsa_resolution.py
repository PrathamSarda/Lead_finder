from automation.models.search_filters import SearchFilters
from automation.resolvers.ddgs_resolver import (
    DDGSWebsiteResolver,
)
from automation.sources.fmcsa.connector import (
    FMCSAConnector,
)


COMPANY_LIMIT = 5


def main() -> None:
    connector = FMCSAConnector()
    resolver = DDGSWebsiteResolver(
        max_results=5,
    )

    companies = connector.search(
        SearchFilters(
            max_results=COMPANY_LIMIT,
        )
    )

    for company in companies:
        print("\n" + "=" * 80)
        print(f"Company: {company.company_name}")
        print(f"Location: {company.location}")

        result = resolver.resolve(
            company_name=company.company_name,
            location=company.location,
        )

        print(f"Success: {result.success}")
        print(f"Website: {result.website}")
        print(
            "Candidates checked: "
            f"{len(result.checked_candidates)}"
        )

        if result.error:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    main()