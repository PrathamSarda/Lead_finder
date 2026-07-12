import pytest

from automation.sources.fmcsa.parser import parse_company


def test_parse_company():
    record = {
        "legal_name": "ABC Trucking",
        "phy_city": "Houston",
        "phy_state": "TX",
        "business_org_desc": "Corporation",
        "total_drivers": "7",
        "power_units": "5",
    }

    company = parse_company(record)

    assert company.company_name == "ABC Trucking"
    assert company.location == "Houston, TX"
    assert company.industry == "Corporation"
    assert company.employee_count == (
        "7 drivers, 5 power units"
    )
    assert company.source == "FMCSA"


def test_parse_company_handles_missing_location():
    record = {
        "legal_name": "Example Transport LLC",
        "total_drivers": "2",
    }

    company = parse_company(record)

    assert company.location is None
    assert company.employee_count == "2 drivers"


def test_parse_company_rejects_missing_company_name():
    with pytest.raises(ValueError):
        parse_company(
            {
                "phy_city": "Dallas",
                "phy_state": "TX",
            }
        )


def test_parse_company_rejects_non_dictionary():
    with pytest.raises(TypeError):
        parse_company([])  # type: ignore[arg-type]