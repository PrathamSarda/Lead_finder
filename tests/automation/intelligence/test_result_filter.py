from __future__ import annotations

from dataclasses import dataclass

import pytest

from automation.intelligence.result_filter import ResultFilter


@dataclass(slots=True)
class FakeCompanyInput:
    name: str


@dataclass(slots=True)
class FakeSearchQuery:
    source: str
    query: str = ""


@dataclass(slots=True)
class FakeSearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass(slots=True)
class FakeCollectedResult:
    query: FakeSearchQuery
    result: FakeSearchResult


@pytest.fixture
def company() -> FakeCompanyInput:
    return FakeCompanyInput(
        name="BROCKMAN TRUCKING INC"
    )


@pytest.fixture
def result_filter() -> ResultFilter:
    return ResultFilter(
        minimum_score=0.55
    )


def make_result(
    *,
    source: str,
    title: str,
    url: str,
    snippet: str = "",
) -> FakeCollectedResult:
    return FakeCollectedResult(
        query=FakeSearchQuery(
            source=source,
            query=(
                f'site:{source}.com '
                f'"BROCKMAN TRUCKING INC"'
            ),
        ),
        result=FakeSearchResult(
            title=title,
            url=url,
            snippet=snippet,
        ),
    )


def test_empty_input_returns_empty_list(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    filtered = result_filter.filter(
        company,
        [],
    )

    assert filtered == []


def test_exact_company_match_is_retained(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com. "
            "Transportation and trucking company."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == [result]


def test_company_name_without_legal_suffix_is_retained(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="website",
        title="Brockman Trucking",
        url="https://brockmantrailers.com",
        snippet=(
            "Official website for Brockman Trucking."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == [result]


def test_unrelated_company_is_rejected(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="linkedin",
        title="ABC Logistics LLC",
        url=(
            "https://www.linkedin.com/company/"
            "abc-logistics"
        ),
        snippet=(
            "A logistics and transportation company "
            "located in Texas."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == []


def test_generic_job_posting_is_rejected(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="generic",
        title="Truck Driver Jobs Near You",
        url="https://example.com/truck-driver-jobs",
        snippet=(
            "Browse trucking jobs, salaries, careers "
            "and apply online."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == []


def test_unrelated_indeed_job_is_rejected(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="indeed",
        title="Diesel Mechanic Jobs",
        url=(
            "https://www.indeed.com/q-diesel-"
            "mechanic-jobs.html"
        ),
        snippet=(
            "Find diesel mechanic jobs and apply today."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == []


def test_relevant_indeed_company_result_can_be_retained(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="indeed",
        title=(
            "Brockman Trucking Inc Company Profile"
        ),
        url=(
            "https://www.indeed.com/cmp/"
            "Brockman-Trucking-Inc"
        ),
        snippet=(
            "Learn about Brockman Trucking Inc, "
            "company information and employee reviews."
        ),
    )

    filtered = result_filter.filter(
        company,
        [result],
    )

    assert filtered == [result]


def test_duplicate_linkedin_urls_are_collapsed(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    first = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com"
        ),
    )

    second = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://linkedin.com/company/"
            "brockman-trucking-inc/"
        ),
        snippet=(
            "Transportation and trucking company."
        ),
    )

    filtered = result_filter.filter(
        company,
        [first, second],
    )

    assert len(filtered) == 1
    assert filtered[0] is first


def test_localized_linkedin_domains_are_deduplicated(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    us_result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com"
        ),
    )

    swiss_result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://ch.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com"
        ),
    )

    dutch_result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://nl.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com"
        ),
    )

    filtered = result_filter.filter(
        company,
        [
            us_result,
            swiss_result,
            dutch_result,
        ],
    )

    assert len(filtered) == 1
    assert filtered[0] is us_result


def test_tracking_parameters_do_not_create_duplicates(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    first = make_result(
        source="website",
        title="Brockman Trucking Inc",
        url=(
            "https://brockmantrailers.com/"
            "?utm_source=google"
        ),
        snippet="Official company website.",
    )

    second = make_result(
        source="website",
        title="Brockman Trucking Inc",
        url="http://www.brockmantrailers.com",
        snippet="Official website.",
    )

    filtered = result_filter.filter(
        company,
        [first, second],
    )

    assert len(filtered) == 1


def test_results_are_ranked_by_relevance(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    generic_result = make_result(
        source="generic",
        title="Brockman Trucking Inc",
        url=(
            "https://directory.example.com/"
            "brockman-trucking"
        ),
        snippet=(
            "Business directory listing for "
            "Brockman Trucking Inc."
        ),
    )

    linkedin_result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com. "
            "Company size: 2-10 employees."
        ),
    )

    filtered = result_filter.filter(
        company,
        [
            generic_result,
            linkedin_result,
        ],
    )

    assert len(filtered) == 2
    assert filtered[0] is linkedin_result
    assert filtered[1] is generic_result


def test_score_is_between_zero_and_one(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    result = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Website: http://www.brockmantrailers.com"
        ),
    )

    score = result_filter.score(
        company,
        result,
    )

    assert 0.0 <= score <= 1.0


def test_exact_match_scores_higher_than_unrelated_result(
    company: FakeCompanyInput,
    result_filter: ResultFilter,
) -> None:
    relevant = make_result(
        source="linkedin",
        title="Brockman Trucking Inc",
        url=(
            "https://www.linkedin.com/company/"
            "brockman-trucking-inc"
        ),
        snippet=(
            "Transportation company with 2-10 employees."
        ),
    )

    unrelated = make_result(
        source="linkedin",
        title="ABC Logistics LLC",
        url=(
            "https://www.linkedin.com/company/"
            "abc-logistics"
        ),
        snippet="Transportation and logistics company.",
    )

    relevant_score = result_filter.score(
        company,
        relevant,
    )

    unrelated_score = result_filter.score(
        company,
        unrelated,
    )

    assert relevant_score > unrelated_score


def test_invalid_minimum_score_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_score",
    ):
        ResultFilter(
            minimum_score=1.5
        )


def test_missing_company_name_raises_error(
    result_filter: ResultFilter,
) -> None:
    invalid_company = FakeCompanyInput(
        name=""
    )

    with pytest.raises(
        ValueError,
        match="non-empty 'name'",
    ):
        result_filter.filter(
            invalid_company,
            [],
        )
