from urllib.parse import unquote

import phonenumbers
from bs4 import BeautifulSoup
from phonenumbers import PhoneNumberFormat


DEFAULT_REGION = "US"


def _extract_tel_links(soup: BeautifulSoup) -> list[str]:
    """
    Extract raw phone-number candidates from tel: links.
    """

    phone_numbers = []

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()

        if not href.lower().startswith("tel:"):
            continue

        phone_number = unquote(href[4:]).strip()

        if phone_number:
            phone_numbers.append(phone_number)

    return phone_numbers


def _extract_text_candidates(
    text: str,
    region: str,
) -> list[str]:
    """
    Extract possible phone numbers from visible webpage text.
    """

    candidates = []

    for match in phonenumbers.PhoneNumberMatcher(text, region):
        candidates.append(match.raw_string)

    return candidates


def _normalize_phone_number(
    phone_number: str,
    region: str,
) -> str | None:
    """
    Validate and normalize one phone number to E.164 format.

    Example:
        (212) 555-0123 -> +12125550123
    """

    try:
        parsed_number = phonenumbers.parse(phone_number, region)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_possible_number(parsed_number):
        return None

    if not phonenumbers.is_valid_number(parsed_number):
        return None

    return phonenumbers.format_number(
        parsed_number,
        PhoneNumberFormat.E164,
    )


def _deduplicate(phone_numbers: list[str]) -> list[str]:
    """
    Remove duplicate phone numbers while preserving order.
    """

    seen = set()
    unique_phone_numbers = []

    for phone_number in phone_numbers:
        if phone_number in seen:
            continue

        seen.add(phone_number)
        unique_phone_numbers.append(phone_number)

    return unique_phone_numbers


def extract_phone_numbers(
    html: str,
    region: str = DEFAULT_REGION,
) -> list[str]:
    """
    Extract, validate, normalize, and deduplicate phone numbers
    from an HTML document.

    Phone numbers are returned in E.164 format.
    """

    if not isinstance(html, str) or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")

    visible_text = soup.get_text(" ", strip=True)

    candidates = []

    candidates.extend(
        _extract_text_candidates(
            text=visible_text,
            region=region,
        )
    )

    candidates.extend(_extract_tel_links(soup))

    normalized_phone_numbers = []

    for candidate in candidates:
        normalized_phone_number = _normalize_phone_number(
            phone_number=candidate,
            region=region,
        )

        if normalized_phone_number is not None:
            normalized_phone_numbers.append(
                normalized_phone_number
            )

    normalized_phone_numbers = _deduplicate(
        normalized_phone_numbers
    )

    normalized_phone_numbers.sort()

    return normalized_phone_numbers
