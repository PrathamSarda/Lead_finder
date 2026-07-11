from automation.enrichment.contact_page_finder import (
    find_contact_pages,
)


def test_find_contact_pages():
    html = """
    <html>
        <body>

            <a href="/contact">
                Contact
            </a>

            <a href="/about">
                About
            </a>

            <a href="/team">
                Team
            </a>

            <a href="/support">
                Support
            </a>

            <a href="/help">
                Help
            </a>

        </body>
    </html>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert pages == [
        "https://company.com/contact",
        "https://company.com/about",
        "https://company.com/team",
        "https://company.com/support",
        "https://company.com/help",
    ]


def test_external_links_are_ignored():
    html = """
    <a href="https://google.com/contact">
        Contact
    </a>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert pages == []


def test_duplicate_links_are_removed():
    html = """
    <a href="/contact">
        Contact
    </a>

    <a href="/contact">
        Contact
    </a>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert pages == [
        "https://company.com/contact"
    ]


def test_fragments_are_removed():
    html = """
    <a href="/contact#top">
        Contact
    </a>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert pages == [
        "https://company.com/contact"
    ]


def test_file_downloads_are_ignored():
    html = """
    <a href="/contact.pdf">
        Contact
    </a>

    <a href="/contact">
        Contact
    </a>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert pages == [
        "https://company.com/contact"
    ]


def test_maximum_pages_returned():
    html = """
    <a href="/contact">Contact</a>
    <a href="/about">About</a>
    <a href="/team">Team</a>
    <a href="/support">Support</a>
    <a href="/help">Help</a>
    <a href="/locations">Locations</a>
    <a href="/company">Company</a>
    """

    pages = find_contact_pages(
        html,
        "https://company.com",
    )

    assert len(pages) == 5