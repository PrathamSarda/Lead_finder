from automation.enrichment.email_extractor import extract_emails


def test_extract_emails_from_text_and_mailto_links():
    html = """
    <html>
        <body>
            <p>Sales: sales@company.com</p>

            <p>Support: SUPPORT@company.com</p>

            <a href="mailto:info@company.com">
                Contact
            </a>

            <a href="mailto:jobs@company.com?subject=Resume">
                Jobs
            </a>

            <p>example@example.com</p>

            <p>sales@company.com</p>
        </body>
    </html>
    """

    emails = extract_emails(html)

    assert emails == [
        "info@company.com",
        "jobs@company.com",
        "sales@company.com",
        "support@company.com",
    ]