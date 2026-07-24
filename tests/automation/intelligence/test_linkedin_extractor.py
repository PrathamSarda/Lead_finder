from automation.intelligence.extractors.linkedin import LinkedInExtractor
from automation.intelligence.models import (
    CompanyInput,
    CollectedResult,
    SearchQuery,
    SearchResult,
)


def test_can_extract():
    extractor = LinkedInExtractor()

    result = CollectedResult(
        query=SearchQuery(
            source="linkedin",
            query="",
        ),
        result=SearchResult(
            title="Brockman Trucking Inc",
            url="https://www.linkedin.com/company/brockman-trucking-inc",
            snippet="Website: http://www.brockmantrailers.com",
        ),
    )

    assert extractor.can_extract(result)


def test_extract():
    extractor = LinkedInExtractor()

    company = CompanyInput(
        name="BROCKMAN TRUCKING INC",
    )

    result = CollectedResult(
        query=SearchQuery(
            source="linkedin",
            query="",
        ),
        result=SearchResult(
            title="Brockman Trucking Inc",
            url="https://www.linkedin.com/company/brockman-trucking-inc",
            snippet="Website: http://www.brockmantrailers.com",
        ),
    )

    evidence = extractor.extract(
        company,
        [result],
    )

    assert len(evidence) == 1

    assert evidence[0].website == "http://www.brockmantrailers.com"

    assert evidence[0].company_name == "Brockman Trucking Inc"

    assert evidence[0].confidence == 0.95

    assert evidence[0].source == "linkedin"