import pytest

from automation.verification.directory_registry import (
    evaluate_domain_plausibility,
    is_civic_or_gov_domain,
    is_directory_domain,
    is_foreign_cctld,
    normalize_domain,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://truckingdatabase.com/carrier/123", True),
        ("https://www.brokersnapshot.com/profile", True),
        ("https://bestcrosscountrymovers.com", True),
        ("https://crosscountrymovers.com/reviews", True),
        ("https://safer.fmcsa.dot.gov/query.asp", True),
        ("https://cherokeeculvert.com/", False),
        ("https://wjbeitler.com/", False),
    ],
)
def test_is_directory_domain(url, expected):
    assert is_directory_domain(url) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://mckeesrocks.org", True),
        ("https://boroughofmckeesrocks.org", True),
        ("https://cityofatlanta.gov", True),
        ("https://acmebrickmaterials.com", False),
    ],
)
def test_is_civic_or_gov_domain(url, expected):
    assert is_civic_or_gov_domain(url) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://james-austin.co.uk", True),
        ("https://example.de", True),
        ("https://company.ca", True),
        ("https://cherokeeculvert.com", False),
    ],
)
def test_is_foreign_cctld(url, expected):
    assert is_foreign_cctld(url) is expected


def test_evaluate_domain_plausibility_rejects_directory():
    plausible, reason = evaluate_domain_plausibility("https://truckingdatabase.com")
    assert plausible is False
    assert "directory_domain" in reason


def test_evaluate_domain_plausibility_rejects_foreign_cctld():
    plausible, reason = evaluate_domain_plausibility("http://james-austin.co.uk")
    assert plausible is False
    assert "foreign_cctld" in reason


def test_evaluate_domain_plausibility_accepts_clean_domain():
    plausible, reason = evaluate_domain_plausibility("https://cherokeeculvert.com")
    assert plausible is True
    assert reason is None
