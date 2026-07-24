from __future__ import annotations


def build_search_queries(
    company_name: str,
    location: str | None,
) -> list[str]:
    """
    Build progressively broader company-website search queries.

    Queries are ordered from the most precise to the broadest.
    The resolver should stop immediately when a homepage passes
    validation.
    """

    company = company_name.strip()

    if not company:
        return []

    queries: list[str] = []

    city = ""
    state = ""

    if location:
        normalized_location = location.strip()

        if "," in normalized_location:
            city, state = [
                part.strip()
                for part in normalized_location.split(",", 1)
            ]
        else:
            city = normalized_location

    # Query 1:
    # This was the query that previously found Cherokee Culvert.
    if city and state:
        queries.append(
            f'"{company}" "{city}" "{state}" official website'
        )
    elif city:
        queries.append(
            f'"{company}" "{city}" official website'
        )

    # Query 2:
    # Exact company and location without forcing the word "official".
    if city and state:
        queries.append(
            f'"{company}" "{city}" "{state}"'
        )
    elif city:
        queries.append(
            f'"{company}" "{city}"'
        )

    # Query 3:
    # Useful when the official site is not strongly associated
    # with the supplied city in Google's index.
    queries.append(
        f'"{company}" official website'
    )

    # Query 4:
    # Broad fallback for difficult companies such as BioLab.
    queries.append(company)

    # Preserve order while preventing duplicate API requests.
    return list(dict.fromkeys(queries))