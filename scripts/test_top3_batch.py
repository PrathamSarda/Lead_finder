
from automation.intelligence.company_pipeline import CompanyPipeline
from automation.intelligence.models import CompanyInput


COMPANIES = [
    CompanyInput(
        name="M J Ouellette Trucking",
    ),
    CompanyInput(
        name="International Freight Systems Inc",
    ),
    CompanyInput(
        name="U-Haul Co Memphis Tenn",
        city="Memphis",
        state="TN",
    ),
    CompanyInput(
        name="D & H Welding Supply Co Inc",
    ),
    CompanyInput(
        name="Airco Welding Supply",
    ),
    CompanyInput(
        name="Liberty Fuel Co",
    ),
    CompanyInput(
        name="Dixon Paving Corporation",
        city="York",
        state="ME",
    ),
    CompanyInput(
        name="Brockman Trucking Inc",
        city="Afton",
        state="MN",
    ),
    CompanyInput(
        name="Lawrence L Lyons",
        city="Kooskia",
        state="ID",
    ),
    CompanyInput(
        name="Viking Waterbeds Inc",
        city="Saint Joseph",
        state="MN",
    ),
]


def main() -> None:
    pipeline = CompanyPipeline()
    results = []

    for index, company in enumerate(COMPANIES, start=1):
        print("\n" + "=" * 90)
        print(f"COMPANY {index}/{len(COMPANIES)}: {company.name}")
        print("=" * 90)

        try:
            final = pipeline.run(company)

            print("\nTop 3 candidates:")
            if not pipeline.last_candidates:
                print("No candidates found.")
            else:
                for rank, candidate in enumerate(
                    pipeline.last_candidates,
                    start=1,
                ):
                    result = candidate.result
                    print(
                        f"{rank}. {result.title}\n"
                        f"   URL: {result.url}\n"
                        f"   Destination: {getattr(result, 'destination', None)}"
                    )

            if final is not None:
                results.append({
                    "company": company.name,
                    "website": final.website,
                    "email": final.email,
                    "phone": final.phone,
                    "sources": final.sources,
                    "status": "Evidence extracted",
                })
            else:
                results.append({
                    "company": company.name,
                    "website": None,
                    "email": None,
                    "phone": None,
                    "sources": None,
                    "status": "No final evidence",
                })

        except Exception as exc:
            print(f"ERROR processing {company.name}: {exc}")
            results.append({
                "company": company.name,
                "website": None,
                "email": None,
                "phone": None,
                "sources": None,
                "status": f"Error: {exc}",
            })

    print("\n\n" + "=" * 100)
    print("BATCH TEST SUMMARY")
    print("=" * 100)

    for result in results:
        print(f"\nCompany: {result['company']}")
        print(f"Status:  {result['status']}")
        print(f"Website: {result['website']}")
        print(f"Email:   {result['email']}")
        print(f"Phone:   {result['phone']}")
        print(f"Sources: {result['sources']}")

    completed = sum(
        1 for result in results
        if result["status"] == "Evidence extracted"
    )
    print("\n" + "-" * 100)
    print(f"Companies tested: {len(COMPANIES)}")
    print(f"With evidence:    {completed}")
    print(f"Without evidence: {len(COMPANIES) - completed}")


if __name__ == "__main__":
    main()