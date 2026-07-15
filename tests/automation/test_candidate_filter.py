from automation.resolvers.candidate_filter import (
    evaluate_candidate_url,
    normalize_hostname,
)


def test_normalize_hostname_removes_www():
    assert normalize_hostname(
        "https://www.example.com/contact"
    ) == "example.com"


def test_official_company_domain_is_accepted():
    result = evaluate_candidate_url(
        "https://cherokeeculvert.com/contact/"
    )

    assert result.accepted is True
    assert result.reason is None


def test_linkedin_is_rejected():
    result = evaluate_candidate_url(
        "https://www.linkedin.com/company/example"
    )

    assert result.accepted is False
    assert result.reason == "excluded_domain"


def test_truck_directory_is_rejected():
    result = evaluate_candidate_url(
        "https://truckcarrierhub.com/GA/USDOT-111"
    )

    assert result.accepted is False
    assert result.reason == "excluded_domain"


def test_unknown_directory_path_is_rejected():
    result = evaluate_candidate_url(
        "https://unknown-site.test/company/example"
    )

    assert result.accepted is False
    assert result.reason == "directory_path_pattern"


def test_unsupported_scheme_is_rejected():
    result = evaluate_candidate_url(
        "ftp://example.com/file"
    )

    assert result.accepted is False
    assert result.reason == "unsupported_scheme"


def test_domain_with_directory_pattern_is_rejected():
    result = evaluate_candidate_url(
        "https://georgia-companyregistry.test/example"
    )

    assert result.accepted is False
    assert result.reason == (
        "directory_domain_pattern"
    )