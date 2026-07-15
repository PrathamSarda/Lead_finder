from urllib.parse import urlparse

from bs4 import BeautifulSoup
from ddgs import DDGS

from automation.enrichment.website_fetcher import fetch_website
from automation.resolvers.scorer import score_search_result
from automation.resolvers.validator import (
    validate_company_homepage,
)


COMPANIES = [
    ("GLEN DYER", "MOBILE, AL"),
    (
        "CHEROKEE CULVERT COMPANY INC",
        "MACON, GA",
    ),
    (
        "CAIN AM BICKLEY LLC",
        "MARSHALLVILLE, GA",
    ),
    ("BIOLAB INC", "LAWRENCEVILLE, GA"),
    (
        "CWT FARMS INTERNATIONAL INC",
        "GAINESVILLE, GA",
    ),
]


def build_query(
    company_name: str,
    location: str,
) -> str:
    return (
        f'"{company_name}" '
        f'"{location}" '
        "website"
    )


def root_url(url: str) -> str | None:
    parsed = urlparse(url)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        return None

    return f"{parsed.scheme}://{parsed.netloc}/"


def extract_page_summary(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    first_heading = soup.find(["h1", "h2"])

    heading = (
        first_heading.get_text(" ", strip=True)
        if first_heading
        else ""
    )

    return title, heading


def main() -> None:
    for company_name, location in COMPANIES:
        query = build_query(
            company_name,
            location,
        )

        print("\n" + "=" * 100)
        print(f"COMPANY: {company_name}")
        print(f"QUERY: {query}")

        try:
            results = list(
                DDGS().text(
                    query=query,
                    region="us-en",
                    safesearch="moderate",
                    max_results=10,
                    backend="auto",
                )
            )
        except Exception as exc:
            print(f"SEARCH ERROR: {exc}")
            continue

        ranked_results = []

        for result in results:
            title = str(
                result.get("title", "")
            ).strip()

            url = str(
                result.get("href", "")
            ).strip()

            description = str(
                result.get("body", "")
            ).strip()

            if not url:
                continue

            score = score_search_result(
                company_name=company_name,
                location=location,
                title=title,
                url=url,
                description=description,
            )

            ranked_results.append(
                (
                    score,
                    title,
                    url,
                )
            )

        ranked_results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        for index, (
            score,
            search_title,
            candidate_url,
        ) in enumerate(
            ranked_results[:5],
            start=1,
        ):
            candidate_root = root_url(
                candidate_url
            )

            print("\n" + "-" * 100)
            print(f"RESULT #{index}")
            print(f"SCORE: {score}")
            print(f"SEARCH TITLE: {search_title}")
            print(f"SEARCH URL: {candidate_url}")
            print(f"ROOT URL: {candidate_root}")

            if candidate_root is None:
                print("FETCH: skipped — invalid root URL")
                continue

            fetch_result = fetch_website(
                candidate_root
            )

            print(
                f"FETCH SUCCESS: "
                f"{fetch_result.success}"
            )
            print(
                f"STATUS CODE: "
                f"{fetch_result.status_code}"
            )
            print(
                f"FINAL URL: "
                f"{fetch_result.final_url}"
            )
            print(
                f"FETCH ERROR: "
                f"{fetch_result.error}"
            )

            html = fetch_result.html or ""

            print(f"HTML LENGTH: {len(html)}")

            if not fetch_result.success:
                continue

            title, heading = extract_page_summary(
                html
            )

            print(f"PAGE TITLE: {title}")
            print(f"FIRST HEADING: {heading}")

            validated = validate_company_homepage(
                company_name=company_name,
                location=location,
                url=(
                    fetch_result.final_url
                    or candidate_root
                ),
                html=html,
            )

            print(f"VALIDATED: {validated}")


if __name__ == "__main__":
    main()