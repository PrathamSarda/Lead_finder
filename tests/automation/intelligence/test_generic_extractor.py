from automation.intelligence.extractors.generic import GenericExtractor
from automation.intelligence.models import (
    CollectedResult,
    CompanyInput,
    SearchQuery,
)
from automation.resolvers.providers.base import SearchResult
import pytest


def make_collected_result(
    *,
    title: str = "",
    url: str = "",
    snippet: str = "",
    source: str = "website",
) -> CollectedResult:
    return CollectedResult(
        query=SearchQuery(
            source=source,
            query="test query",
        ),
        result=SearchResult(
        provider="test",
        title=title,
        url=url,
        snippet=snippet,
        position=1,
        ),
    )


def test_can_extract_generic_website():
    extractor = GenericExtractor()

    result = make_collected_result(
        title="Brockman Trucking Inc",
        url="https://www.brockmantrucking.com/about",
        snippet="Transportation company in Afton, MN.",
    )

    assert extractor.can_extract(result)


def test_rejects_linkedin_company_result():
    extractor = GenericExtractor()

    result = make_collected_result(
        title="Brockman Trucking Inc",
        url="https://www.linkedin.com/company/brockman-trucking-inc",
        snippet="Company profile",
        source="linkedin",
    )

    assert not extractor.can_extract(result)


def test_rejects_glassdoor_result():
    extractor = GenericExtractor()

    result = make_collected_result(
        title="Brockman Trucking Reviews",
        url="https://www.glassdoor.com/Reviews/Brockman-Trucking-Reviews",
        snippet="Employee reviews",
        source="glassdoor",
    )

    assert not extractor.can_extract(result)


def test_extracts_company_evidence():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="BROCKMAN TRUCKING INC",
        city="Afton",
        state="MN",
    )

    result = make_collected_result(
        title="Brockman Trucking Inc | Transportation Services",
        url="https://www.brockmantrucking.com/about-us",
        snippet=(
            "Family-owned transportation company in Afton, MN. "
            "Email info@brockmantrucking.com or call (651) 555-1234."
        ),
    )

    evidence = extractor.extract(
        company,
        [result],
    )

    assert len(evidence) == 1

    item = evidence[0]

    assert item.source == "generic"
    assert item.company_name == "Brockman Trucking Inc"
    assert item.website == "https://brockmantrucking.com"
    assert item.email == "info@brockmantrucking.com"
    assert item.phone == "(651) 555-1234"
    assert item.location == "Afton, MN"
    assert item.confidence == 0.95


def test_uses_company_location_as_fallback():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Brockman Trucking Inc",
        city="Afton",
        state="MN",
    )

    result = make_collected_result(
        title="Brockman Trucking Inc",
        url="https://brockmantrucking.com",
        snippet="Regional transportation and logistics services.",
    )

    evidence = extractor.extract(
        company,
        [result],
    )

    assert evidence[0].location == "Afton, MN"


def test_extracts_base_website_from_page_url():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://www.example.com/contact/team?source=google",
        snippet="Official contact page.",
    )

    evidence = extractor.extract(
        company,
        [result],
    )

    assert evidence[0].website == "https://example.com"


def test_deduplicates_same_page_url():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    first = make_collected_result(
        title="Example Company",
        url="https://www.example.com/about",
        snippet="Official website.",
    )

    duplicate = make_collected_result(
        title="Example Company About",
        url="https://example.com/about/",
        snippet="Company information.",
    )

    evidence = extractor.extract(
        company,
        [first, duplicate],
    )

    assert len(evidence) == 1


def test_returns_empty_for_unsupported_results():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company LinkedIn",
        url="https://linkedin.com/company/example-company",
        snippet="LinkedIn company page.",
        source="linkedin",
    )

    assert extractor.extract(company, [result]) == []


def test_confidence_increases_when_contact_details_exist():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    without_contact = make_collected_result(
        title="Unrelated title",
        url="https://example.com",
        snippet="Company services.",
    )

    with_contact = make_collected_result(
        title="Unrelated title",
        url="https://example.org",
        snippet="Email contact@example.org and call 212-555-1234.",
    )

    evidence = extractor.extract(
        company,
        [without_contact, with_contact],
    )

    assert evidence[1].confidence > evidence[0].confidence
def test_rejects_empty_url():
    extractor = GenericExtractor()

    result = make_collected_result(
        title="Example Company",
        url="",
        snippet="Official website.",
    )

    assert not extractor.can_extract(result)


def test_rejects_social_media_domains():
    extractor = GenericExtractor()

    domains = [
        "https://facebook.com/example",
        "https://www.instagram.com/example",
        "https://x.com/example",
        "https://youtube.com/@example",
    ]

    for url in domains:
        result = make_collected_result(
            title="Example Company",
            url=url,
            snippet="Social media page.",
        )

        assert not extractor.can_extract(result)


def test_extracts_email_in_lowercase():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Contact SALES@EXAMPLE.COM for assistance.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].email == "sales@example.com"


def test_returns_none_when_email_is_missing():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Official company website.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].email is None


def test_extracts_phone_without_country_code():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Call us at 212-555-1234.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].phone == "212-555-1234"


def test_extracts_phone_with_us_country_code():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Contact us at +1 212 555 1234.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].phone == "+1 212 555 1234"


def test_extracts_location_from_plain_city_and_state():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Example Company is based in Dallas, TX.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].location == "Dallas, TX"


def test_extracts_multiword_city():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet="Serving customers from Salt Lake City, UT.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].location == "Salt Lake City, UT"


def test_extracts_company_name_before_dash():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company - Logistics and Transportation",
        url="https://example.com",
        snippet="Official company website.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].company_name == "Example Company"


def test_extracts_company_name_before_pipe():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company | Official Website",
        url="https://example.com",
        snippet="Official company website.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].company_name == "Example Company"


def test_falls_back_to_input_company_name_when_title_is_empty():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="",
        url="https://example.com",
        snippet="Official company website.",
    )

    evidence = extractor.extract(company, [result])

    assert evidence[0].company_name == "Example Company"


def test_removes_query_parameters_during_deduplication():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    first = make_collected_result(
        title="Example Company",
        url="https://example.com/about?utm_source=google",
        snippet="Official website.",
    )

    second = make_collected_result(
        title="Example Company About",
        url="https://www.example.com/about?ref=search",
        snippet="Company profile.",
    )

    evidence = extractor.extract(company, [first, second])

    assert len(evidence) == 1


def test_does_not_merge_different_pages_on_same_domain():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    about = make_collected_result(
        title="About Example Company",
        url="https://example.com/about",
        snippet="About page.",
    )

    contact = make_collected_result(
        title="Contact Example Company",
        url="https://example.com/contact",
        snippet="Contact page.",
    )

    evidence = extractor.extract(company, [about, contact])

    assert len(evidence) == 2


def test_confidence_never_exceeds_one():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company",
        url="https://example.com",
        snippet=(
            "Located in Austin, TX. "
            "Email info@example.com or call 512-555-1234."
        ),
    )

    evidence = extractor.extract(company, [result])

    assert 0.0 <= evidence[0].confidence <= 1.0


def test_preserves_original_result_metadata():
    extractor = GenericExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    result = make_collected_result(
        title="Example Company | Official Website",
        url="https://example.com/about",
        snippet="Official company information.",
    )

    evidence = extractor.extract(company, [result])

    item = evidence[0]

    assert item.title == "Example Company | Official Website"
    assert item.url == "https://example.com/about"
    assert item.snippet == "Official company information."




@pytest.mark.parametrize(
    "url",
    [
        "https://www.zoominfo.com/c/example/123",
        "https://www.crunchbase.com/organization/example",
        "https://dotsearch.us/carrier/123",
        "https://www.fyple.com/company/example",
        "https://www.osha.gov/example",
        "https://safer.fmcsa.dot.gov/query.asp?id=123",
        "https://reviews.birdeye.com/example",
        "https://newbizbot.ai/company/example",
    ],
)
def test_rejects_directory_and_government_domains(
    url: str,
):
    extractor = GenericExtractor()

    result = make_collected_result(
        title="Example Company",
        url=url,
        snippet="Example Company details",
    )

    evidence = extractor.extract(
        CompanyInput(name="Example Company"),
        [result],
    )

    assert evidence == []