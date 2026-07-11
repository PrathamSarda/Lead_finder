from urllib.parse import unquote

from bs4 import BeautifulSoup

from automation.enrichment.regex_patterns import EMAIL_PATTERN


INVALID_EMAILS = {
    "example@example.com",
    "test@test.com",
    "email@example.com",
}


def _extract_regex_emails(text: str) -> list[str]:
    return EMAIL_PATTERN.findall(text)


def _extract_mailto_emails(soup: BeautifulSoup) -> list[str]:
    emails = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0]
            email = unquote(email)

            if email:
                emails.append(email)

    return emails


def _normalize(emails: list[str]) -> list[str]:
    normalized = []

    for email in emails:
        email = email.strip().lower()

        if email:
            normalized.append(email)

    return normalized


def _filter_invalid(emails: list[str]) -> list[str]:
    filtered = []

    for email in emails:
        if email in INVALID_EMAILS:
            continue

        filtered.append(email)

    return filtered


def _deduplicate(emails: list[str]) -> list[str]:
    seen = set()
    result = []

    for email in emails:
        if email not in seen:
            seen.add(email)
            result.append(email)

    return result


def extract_emails(html: str) -> list[str]:
    """
    Extract all valid email addresses from an HTML document.
    """

    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ")

    emails = []

    emails.extend(_extract_regex_emails(text))

    emails.extend(_extract_mailto_emails(soup))

    emails = _normalize(emails)

    emails = _filter_invalid(emails)

    emails = _deduplicate(emails)

    emails.sort()

    return emails