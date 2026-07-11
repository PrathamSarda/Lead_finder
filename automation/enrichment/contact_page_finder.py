from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

CONTACT_KEYWORDS = {
    "contact",
    "contact-us",
    "contact us",
    "about",
    "about-us",
    "about us",
    "support",
    "help",
    "reach us",
    "get in touch",
    "team",
    "our team",
    "company",
    "locations",
    "office",
}

MAX_CONTACT_PAGES = 5

IGNORED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".zip",
    ".xml",
    ".json",
}


def find_contact_pages(html: str, base_url: str) -> list[str]:
    """Return relevant internal contact/about/support page URLs."""

    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc.lower()
    pages: list[str] = []

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()
        text = link.get_text(" ", strip=True).lower()
        href_lower = href.lower()

        if not href:
            continue

        is_relevant = any(
            keyword in text or keyword.replace(" ", "-") in href_lower
            for keyword in CONTACT_KEYWORDS
        )

        if not is_relevant:
            continue

        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        # Avoid unrelated external sites and non-HTTP links.
        if parsed_url.scheme not in {"http", "https"}:
            continue

        if parsed_url.netloc.lower() != base_domain:
            continue

        clean_url = full_url.split("#", maxsplit=1)[0]
        if any(
        clean_url.lower().endswith(extension)
        for extension in IGNORED_EXTENSIONS
):
            continue

        if clean_url not in pages:
            pages.append(clean_url)
    priority = (
        "contact",
        "contact-us",
        "get-in-touch",
        "about",
        "team",
        "support",
        "help",
    )

    pages.sort(
        key=lambda page: min(
            (
                index
                for index, keyword in enumerate(priority)
                if keyword in page.lower()
            ),
            default=len(priority),
            )
        )
    return pages[:MAX_CONTACT_PAGES]