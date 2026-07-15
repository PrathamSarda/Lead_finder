import re
from urllib.parse import urlparse

from automation.models.email_priority_result import (
    EmailPriorityResult,
)


FREE_EMAIL_DOMAINS = {
    "aol.com",
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "mail.com",
    "msn.com",
    "outlook.com",
    "proton.me",
    "protonmail.com",
    "yahoo.com",
    "ymail.com",
}

HIGH_PRIORITY_LOCAL_PARTS = {
    "info": 100,
    "contact": 95,
    "sales": 90,
    "hello": 88,
    "office": 85,
    "support": 80,
    "admin": 75,
    "accounts": 72,
    "accounting": 72,
    "billing": 70,
    "service": 68,
    "customerservice": 68,
    "enquiries": 65,
    "inquiries": 65,
    "general": 60,
}

LOW_PRIORITY_LOCAL_PARTS = {
    "careers",
    "jobs",
    "hr",
    "privacy",
    "legal",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "webmaster",
}

REJECTED_LOCAL_PARTS = {
    "example",
    "test",
    "testing",
    "sample",
    "yourname",
    "email",
}

EMAIL_PATTERN = re.compile(
    r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$",
    re.IGNORECASE,
)


def _normalize_email(email: str) -> str:
    """
    Normalize one email address for comparison and storage.
    """

    return email.strip().lower()


def _split_email(email: str) -> tuple[str, str] | None:
    """
    Return the local part and domain of a valid email.
    """

    normalized_email = _normalize_email(email)

    if not EMAIL_PATTERN.fullmatch(normalized_email):
        return None

    local_part, domain = normalized_email.rsplit(
        "@",
        maxsplit=1,
    )

    return local_part, domain


def _website_domain(
    website: str | None,
) -> str | None:
    """
    Extract the hostname from a company website.
    """

    if not website:
        return None

    parsed_url = urlparse(website)

    hostname = parsed_url.netloc.lower()

    if not hostname:
        return None

    return hostname.removeprefix("www.")


def _is_same_or_subdomain(
    email_domain: str,
    website_domain: str,
) -> bool:
    """
    Compare an email domain with the company's website domain.
    """

    return (
        email_domain == website_domain
        or email_domain.endswith(
            f".{website_domain}"
        )
        or website_domain.endswith(
            f".{email_domain}"
        )
    )


def _score_email(
    email: str,
    website_domain: str | None,
) -> int:
    """
    Score an email based on role and domain relevance.
    """

    split_email = _split_email(email)

    if split_email is None:
        return -1_000

    local_part, domain = split_email
    compact_local_part = re.sub(
        r"[^a-z0-9]",
        "",
        local_part,
    )

    if (
        local_part in REJECTED_LOCAL_PARTS
        or compact_local_part in REJECTED_LOCAL_PARTS
    ):
        return -1_000

    score = 0

    if website_domain and _is_same_or_subdomain(
        email_domain=domain,
        website_domain=website_domain,
    ):
        score += 100

    if domain in FREE_EMAIL_DOMAINS:
        score -= 25

    if local_part in HIGH_PRIORITY_LOCAL_PARTS:
        score += HIGH_PRIORITY_LOCAL_PARTS[
            local_part
        ]
    elif compact_local_part in HIGH_PRIORITY_LOCAL_PARTS:
        score += HIGH_PRIORITY_LOCAL_PARTS[
            compact_local_part
        ]

    if (
        local_part in LOW_PRIORITY_LOCAL_PARTS
        or compact_local_part in LOW_PRIORITY_LOCAL_PARTS
    ):
        score -= 40

    if "." in local_part or "_" in local_part:
        score += 15

    if any(character.isdigit() for character in local_part):
        score -= 5

    return score


def prioritize_emails(
    emails: list[str],
    website: str | None = None,
) -> EmailPriorityResult:
    """
    Rank and classify discovered email addresses.

    Company-domain emails are preferred. Generic role-based business
    emails such as info@ and contact@ receive the highest priority.
    Free-mail addresses are retained separately rather than discarded.
    """

    website_domain = _website_domain(website)

    normalized_emails = sorted(
        {
            _normalize_email(email)
            for email in emails
            if isinstance(email, str)
            and email.strip()
        }
    )

    business_candidates: list[
        tuple[int, str]
    ] = []

    personal_candidates: list[
        tuple[int, str]
    ] = []

    rejected_emails: list[str] = []

    for email in normalized_emails:
        split_email = _split_email(email)

        if split_email is None:
            rejected_emails.append(email)
            continue

        _, domain = split_email

        score = _score_email(
            email=email,
            website_domain=website_domain,
        )

        if score <= -1_000:
            rejected_emails.append(email)
            continue

        if domain in FREE_EMAIL_DOMAINS:
            personal_candidates.append(
                (
                    score,
                    email,
                )
            )
        else:
            business_candidates.append(
                (
                    score,
                    email,
                )
            )

    business_candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    personal_candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    business_emails = [
        email
        for _, email in business_candidates
    ]

    personal_emails = [
        email
        for _, email in personal_candidates
    ]

    primary_email = None

    if business_emails:
        primary_email = business_emails[0]
    elif personal_emails:
        primary_email = personal_emails[0]

    return EmailPriorityResult(
        primary_email=primary_email,
        business_emails=business_emails,
        personal_emails=personal_emails,
        rejected_emails=rejected_emails,
    )