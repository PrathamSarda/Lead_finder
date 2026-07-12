import pytest

from automation.sources.fmcsa.filters import (
    filter_company_records,
    is_active_company,
    is_qualified_company,
    is_small_operator,
    is_us_company,
)


def build_record(**overrides):
    record = {
        "legal_name": "Small Logistics LLC",
        "phy_city": "Dallas",
        "phy_state": "TX",
        "phy_country": "US",
        "status_code": "A",
        "total_drivers": "8",
        "power_units": "6",
        "fleetsize": "C",
    }

    record.update(overrides)

    return record


def test_active_company_is_accepted():
    assert is_active_company(build_record()) is True


def test_inactive_company_is_rejected():
    assert (
        is_active_company(
            build_record(status_code="I")
        )
        is False
    )


def test_us_company_is_accepted():
    assert is_us_company(build_record()) is True


def test_state_is_used_when_country_is_missing():
    assert (
        is_us_company(
            build_record(phy_country="")
        )
        is True
    )


def test_large_driver_count_is_rejected():
    assert (
        is_small_operator(
            build_record(total_drivers="25")
        )
        is False
    )


def test_large_power_unit_count_is_rejected():
    assert (
        is_small_operator(
            build_record(power_units="30")
        )
        is False
    )


def test_fleet_code_is_used_as_fallback():
    record = build_record(
        total_drivers="",
        power_units="",
        fleetsize="H",
    )

    assert is_small_operator(record) is True


def test_large_fleet_code_is_rejected():
    record = build_record(
        total_drivers="",
        power_units="",
        fleetsize="P",
    )

    assert is_small_operator(record) is False


def test_qualified_company_passes_all_filters():
    assert is_qualified_company(build_record()) is True


def test_missing_company_name_is_rejected():
    assert (
        is_qualified_company(
            build_record(legal_name="")
        )
        is False
    )


def test_filter_company_records():
    records = [
        build_record(
            legal_name="Qualified Carrier"
        ),
        build_record(
            legal_name="Inactive Carrier",
            status_code="I",
        ),
        build_record(
            legal_name="Large Carrier",
            total_drivers="100",
        ),
    ]

    filtered_records = filter_company_records(records)

    assert len(filtered_records) == 1
    assert (
        filtered_records[0]["legal_name"]
        == "Qualified Carrier"
    )


def test_invalid_maximum_is_rejected():
    with pytest.raises(ValueError):
        is_small_operator(
            build_record(),
            max_drivers=0,
        )