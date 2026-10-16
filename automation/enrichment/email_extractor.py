import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from automation.enrichment.regex_patterns import EMAIL_PATTERN


def _decode_cfemail(cfemail: str) -> str:
    try:
        r = int(cfemail[:2], 16)
        return "".join([chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2)]).strip().lower()
    except Exception:
        return ""


def _extract_cloudflare_emails(soup: BeautifulSoup) -> list[str]:
    emails = []
    for tag in soup.find_all(attrs={"data-cfemail": True}):
        decoded = _decode_cfemail(str(tag.get("data-cfemail", "")))
        if decoded:
            emails.append(decoded)
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "email-protection#" in href:
            hash_part = href.split("email-protection#", 1)[-1].split("?")[0]
            decoded = _decode_cfemail(hash_part)
            if decoded:
                emails.append(decoded)
    return emails


def _extract_obfuscated_emails(text: str) -> list[str]:
    cleaned = re.sub(r"\s*(\[|\()at(\]|\))\s*", "@", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*(\[|\()dot(\]|\))\s*", ".", cleaned, flags=re.IGNORECASE)
    return EMAIL_PATTERN.findall(cleaned)


INVALID_EMAILS = {
    "example@example.com",
    "test@test.com",
    "email@example.com",
    "user@domain.com",
}

INVALID_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".js",
    ".css",
    ".woff",
    ".woff2",
    ".ttf",
    ".ico",
    ".zip",
)

INVALID_PREFIXES = (
    "sentry",
    "bootstrap",
    "webpack",
    "npm",
)


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

        if any(email.endswith(ext) for ext in INVALID_EXTENSIONS):
            continue

        local_part = email.split("@")[0]
        if any(local_part.startswith(prefix) for prefix in INVALID_PREFIXES):
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

    # Decompose script, style, and metadata tags before extracting text
    for element in soup(["script", "style", "noscript", "svg", "canvas", "template"]):
        element.decompose()

    text = soup.get_text(" ")

    emails = []

    emails.extend(_extract_regex_emails(text))
    emails.extend(_extract_obfuscated_emails(text))
    emails.extend(_extract_mailto_emails(soup))
    emails.extend(_extract_cloudflare_emails(soup))

    emails = _normalize(emails)

    emails = _filter_invalid(emails)

    emails = _deduplicate(emails)

    emails.sort()

    return emails