from automation.resolvers.validator import (
    validate_company_homepage,
)


def test_validator_accepts_matching_company_homepage():
    html = """
    <html>
        <head>
            <title>
                Cherokee Culvert Company
            </title>
        </head>
        <body>
            <h1>Cherokee Culvert</h1>
            <p>
                Culvert and drainage products from
                Macon, Georgia.
            </p>
        </body>
    </html>
    """

    assert validate_company_homepage(
        company_name=(
            "Cherokee Culvert Company Inc"
        ),
        location="Macon, GA",
        url="https://cherokeeculvert.com/",
        html=html,
    ) is True


def test_validator_accepts_biolab_homepage():
    html = """
    <html>
        <head>
            <title>BioLab Inc.</title>
        </head>
        <body>
            <h1>BioLab</h1>
            <p>
                Pool and water-care products.
            </p>
        </body>
    </html>
    """

    assert validate_company_homepage(
        company_name="Biolab Inc",
        location="Lawrenceville, GA",
        url="https://www.biolabinc.com/",
        html=html,
    ) is True


def test_validator_rejects_unrelated_directory():
    html = """
    <html>
        <head>
            <title>Truck Carrier Hub</title>
        </head>
        <body>
            <h1>Carrier Information Database</h1>
            <p>
                Search thousands of transport businesses.
            </p>
        </body>
    </html>
    """

    assert validate_company_homepage(
        company_name="Cain AM Bickley LLC",
        location="Marshallville, GA",
        url=(
            "https://truckcarrierhub.com/"
            "GA/USDOT-111"
        ),
        html=html,
    ) is False


def test_validator_rejects_empty_html():
    assert validate_company_homepage(
        company_name="Example Company LLC",
        location="Dallas, TX",
        url="https://example.com",
        html="",
    ) is False
def test_validator_rejects_page_that_only_mentions_person():
    html = """
    <html>
        <head>
            <title>Mobile Racing Pigeon Club</title>
        </head>
        <body>
            <h1>Club Members</h1>
            <p>Glen Dyer</p>
        </body>
    </html>
    """

    assert validate_company_homepage(
        company_name="Glen Dyer",
        location="Mobile, AL",
        url="https://mobileracingpigeonclub.com/",
        html=html,
    ) is False


def test_validator_rejects_unrelated_site_with_company_listing():
    html = """
    <html>
        <head>
            <title>FreightVet Transportation Directory</title>
        </head>
        <body>
            <h1>Georgia Locations</h1>
            <p>Cherokee Culvert Company Inc</p>
        </body>
    </html>
    """

    assert validate_company_homepage(
        company_name="Cherokee Culvert Company Inc",
        location="Macon, GA",
        url="https://freightvet.com/",
        html=html,
    ) is False