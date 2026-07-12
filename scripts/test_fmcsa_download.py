from automation.sources.fmcsa.downloader import (
    download_company_sample,
)


POSSIBLE_COMPANY_NAME_FIELDS = (
    "legal_name",
    "dba_name",
    "company_name",
    "name",
)


def find_company_name(record: dict) -> str:
    """
    Return the first available company-name field.
    """

    for field_name in POSSIBLE_COMPANY_NAME_FIELDS:
        value = record.get(field_name)

        if value:
            return str(value)

    return "Company name field not found"


def main() -> None:
    records = download_company_sample(limit=10)

    print(f"\nDownloaded {len(records)} FMCSA records.\n")

    for index, record in enumerate(records, start=1):
        company_name = find_company_name(record)

        print(f"{index}. {company_name}")

    if records:
        print("\nAvailable fields in the first record:")

        for field_name in sorted(records[0].keys()):
            print(f"- {field_name}")


if __name__ == "__main__":
    main()