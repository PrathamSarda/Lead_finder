import re

LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "l.l.c",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "pllc",
    "lp",
    "llp",
}


def _clean_name(name: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    meaningful = [t for t in tokens if t not in LEGAL_SUFFIXES]
    if meaningful:
        return " ".join(meaningful).title()
    return name.strip()


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

    cleaned = _clean_name(company)
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

    location_str = f"{city} {state}".strip()

    # Query 1: Clean branded name + location + official website (natural, unquoted)
    if location_str:
        queries.append(f"{cleaned} {location_str} official website")
        queries.append(f'"{cleaned}" "{city}" website' if city else f'"{cleaned}" website')
        queries.append(f"{cleaned} {location_str}")
    else:
        queries.append(f"{cleaned} official website")

    # Query 2: Clean branded name with quotes
    queries.append(f'"{cleaned}" official website')

    # Query 3: Contact and phone page search - finds small businesses that only show up in contact context
    if location_str:
        queries.append(f'"{cleaned}" {location_str} contact phone')
        queries.append(f'"{cleaned}" {state} contact' if state else f'"{cleaned}" contact')
    else:
        queries.append(f'"{cleaned}" contact phone')

    # Query 4: Exact raw company name if different from cleaned
    if cleaned.lower() != company.lower():
        if location_str:
            queries.append(f'"{company}" {location_str}')
        queries.append(company)

    # Query 5: "About" page search - many small businesses appear in "about" pages
    if location_str:
        queries.append(f'{cleaned} {location_str} "about us"')

    # Query 6: State-context search for very regional companies
    if state:
        queries.append(f'"{cleaned}" {state}')

    # Query 7: Website field search - surfaces brand domains that don't match company name.
    # Some directories explicitly show the company's website URL in search snippets
    # (e.g. "Business Website Address www.acmeclay.com" or "austinsbleach.com").
    if location_str:
        queries.append(f'{cleaned} {location_str} website contact')

    # Query 8: Narrow geographic search with quoted city and state
    # Helps surface brand websites for small companies with non-obvious domains
    if city and state:
        queries.append(f'"{cleaned}" "{city}" "{state}"')

    # Query 9: Direct contact search using original company name (catches edge cases)
    queries.append(f'"{company}" contact email phone')

    # Preserve order while preventing duplicate queries.
    return list(dict.fromkeys(queries))