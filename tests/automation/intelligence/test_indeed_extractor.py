from automation.intelligence.extractors.indeed import IndeedExtractor
from automation.intelligence.models import CompanyInput
from tests.automation.intelligence.test_generic_extractor import make_collected_result


def test_accepts_company_profile():
    extractor = IndeedExtractor()

    result = make_collected_result(
        source="indeed",
        title="Working at Brockman",
        url="https://www.indeed.com/cmp/Brockman",
    )

    assert extractor.can_extract(result)


def test_rejects_job_posting():
    extractor = IndeedExtractor()

    result = make_collected_result(
        source="indeed",
        title="Truck Driver",
        url="https://www.indeed.com/viewjob?jk=123",
    )

    assert not extractor.can_extract(result)


def test_rejects_job_search():
    extractor = IndeedExtractor()

    result = make_collected_result(
        source="indeed",
        title="Driver Jobs",
        url="https://www.indeed.com/jobs?q=driver",
    )

    assert not extractor.can_extract(result)


def test_rejects_non_indeed():
    extractor = IndeedExtractor()

    result = make_collected_result(
        title="Company Website",
        url="https://example.com",
    )

    assert not extractor.can_extract(result)

def test_extract_company_profile():
    extractor = IndeedExtractor()

    company = CompanyInput(
            name="BROCKMAN TRUCKING INC",
            city="Afton",
            state="MN",
        )

    result = make_collected_result(
            source="indeed",
            title="Working at Brockman Trucking Inc",
            url="https://www.indeed.com/cmp/Brockman-Trucking",
            snippet="Transportation company",
        )

    evidence = extractor.extract(
            company,
            [result],
        )

    assert len(evidence) == 1

    item = evidence[0]

    assert item.source == "indeed"
    assert item.company_name == "Brockman Trucking Inc"
    assert item.location == "Afton, MN"
    assert item.confidence == 0.85

def test_duplicate_profiles_are_removed():
    extractor = IndeedExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    first = make_collected_result(
        source="indeed",
        title="Working at Example Company",
        url="https://www.indeed.com/cmp/example-company",
    )

    second = make_collected_result(
        source="indeed",
        title="Working at Example Company",
        url="https://www.indeed.com/cmp/example-company/",
    )

    evidence = extractor.extract(
        company,
        [first, second],
    )

    assert len(evidence) == 1
def test_duplicate_profiles_are_removed():
    extractor = IndeedExtractor()

    company = CompanyInput(
        name="Example Company",
    )

    first = make_collected_result(
        source="indeed",
        title="Working at Example Company",
        url="https://www.indeed.com/cmp/example-company",
    )

    second = make_collected_result(
        source="indeed",
        title="Working at Example Company",
        url="https://www.indeed.com/cmp/example-company/",
    )

    evidence = extractor.extract(
        company,
        [first, second],
    )

    assert len(evidence) == 1