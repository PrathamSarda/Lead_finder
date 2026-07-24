from __future__ import annotations

import logging

from automation.resolvers.website_resolver import (
    WebsiteResolver,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)


TEST_COMPANIES = [
    {
        "company_name": "Cherokee Culvert Company",
        "location": "Macon, Georgia",
    },
    {
        "company_name": "BioLab Inc",
        "location": "Lawrenceville, Georgia",
    },
    {
        "company_name": "CWT Farms International Inc",
        "location": "Gainesville, Georgia",
    },
]


def main() -> None:
    resolver = WebsiteResolver(
        acceptance_threshold=90,
        max_validation_candidates=8,
    )

    for test_company in TEST_COMPANIES:
        company_name = test_company["company_name"]
        location = test_company["location"]

        print("\n" + "=" * 70)
        print(f"Company:  {company_name}")
        print(f"Location: {location}")
        print("=" * 70)

        try:
            result = resolver.resolve(
                company_name=company_name,
                location=location,
            )
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        print(f"Found:      {result.found}")
        print(f"Website:    {result.website}")
        print(f"Provider:   {result.provider}")
        print(f"Score:      {result.score}")
        print(f"Validated:  {result.validated}")
        print(f"Reason:     {result.reason}")
        print(
            "Candidates:  "
            f"{result.attempted_candidates}"
        )


if __name__ == "__main__":
    main()