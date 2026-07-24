from automation.resolvers.providers.website_resolver import WebsiteResolver


TEST_COMPANIES = [
    (
        "CHEROKEE CULVERT COMPANY INC",
        "MACON, GA",
    ),
    (
        "BIOLAB INC",
        "LAWRENCEVILLE, GA",
    ),
    (
        "CWT FARMS INTERNATIONAL INC",
        "GAINESVILLE, GA",
    ),
]


def main() -> None:
    resolver = WebsiteResolver()(
        result_count=10,
        validation_limit=5,
    )

    for company_name, location in TEST_COMPANIES:
        print("\n" + "=" * 80)
        print(f"Company: {company_name}")
        print(f"Location: {location}")

        result = resolver.resolve(
            company_name=company_name,
            location=location,
        )

        print(f"Success: {result.success}")
        print(f"Website: {result.website}")
        print(f"Provider: {result.provider}")
        print(f"Query: {result.query}")

        print(
            "Candidates checked: "
            f"{len(result.checked_candidates)}"
        )

        print(
            "Candidates rejected: "
            f"{len(result.rejected_candidates)}"
        )

        print(
            "Candidates fetched: "
            f"{len(result.validated_candidates)}"
        )

        if result.checked_candidates:
            print("\nChecked candidates:")

            for candidate in result.checked_candidates:
                print(f"  - {candidate}")

        if result.rejected_candidates:
            print("\nRejected candidates:")

            for candidate in result.rejected_candidates:
                print(f"  - {candidate}")

        if result.validated_candidates:
            print("\nValidated/fetched candidates:")

            for candidate in result.validated_candidates:
                print(f"  - {candidate}")

        if result.error:
            print(f"\nError: {result.error}")


if __name__ == "__main__":
    main()