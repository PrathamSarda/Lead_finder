from automation.enrichment.phone_extractor import (
    extract_phone_numbers,
)


def test_extract_phone_number_from_visible_text():
    html = """
    <html>
        <body>
            <p>Call us at (212) 555-0123.</p>
        </body>
    </html>
    """

    phone_numbers = extract_phone_numbers(html)

    assert phone_numbers == [
        "+12125550123",
    ]


def test_extract_phone_number_from_tel_link():
    html = """
    <html>
        <body>
            <a href="tel:+14155552671">
                Call us
            </a>
        </body>
    </html>
    """

    phone_numbers = extract_phone_numbers(html)

    assert phone_numbers == [
        "+14155552671",
    ]


def test_phone_numbers_are_deduplicated():
    html = """
    <html>
        <body>
            <p>(212) 555-0123</p>

            <a href="tel:+12125550123">
                Call
            </a>
        </body>
    </html>
    """

    phone_numbers = extract_phone_numbers(html)

    assert phone_numbers == [
        "+12125550123",
    ]


def test_invalid_phone_numbers_are_ignored():
    html = """
    <html>
        <body>
            <p>Reference number: 12345</p>
            <p>Year: 2026</p>
            <p>Invalid: 000-000-0000</p>
        </body>
    </html>
    """

    phone_numbers = extract_phone_numbers(html)

    assert phone_numbers == []


def test_empty_html_returns_empty_list():
    assert extract_phone_numbers("") == []


def test_international_number_with_region():
    html = """
    <html>
        <body>
            <p>London office: 020 7946 0958</p>
        </body>
    </html>
    """

    phone_numbers = extract_phone_numbers(
        html,
        region="GB",
    )

    assert phone_numbers == [
        "+442079460958",
    ]