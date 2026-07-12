from unittest.mock import patch

import pytest

from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import FMCSAConnector


def build_record(
    company_name: str,
    status_code: str = "A",
    drivers: str = "5",
    power_units: str = "4",
) -> dict:
    return {
        "legal_name": company_name,
        "phy_city": "Houston",
        "phy_state": "TX",
        "phy_country": "US",
        "status_code": status_code,
        "business_org_desc": "CORPORATION",
        "total_drivers": drivers,
        "power_units": power_units,
        "fleetsize": "C",
    }


@patch(
    "automation.sources.fmcsa.connector.download_company_sample"
)
def test_connector_returns_only_qualified_company_leads(
    mock_download,
):
    mock_download.return_value = [
        build_record("Qualified Carrier"),
        build_record(
            "Inactive Carrier",
            status_code="I",
        ),
        build_record(
            "Large Carrier",
            drivers="100",
        ),
    ]

    connector = FMCSAConnector()

    companies = connector.search(
        SearchFilters(
            max_results=10,
        )
    )

    assert len(companies) == 1
    assert companies[0].company_name == "Qualified Carrier"
    assert companies[0].source == "FMCSA"


@patch(
    "automation.sources.fmcsa.connector.download_company_sample"
)
def test_connector_overfetches_raw_records(
    mock_download,
):
    mock_download.return_value = []

    connector = FMCSAConnector()

    connector.search(
        SearchFilters(
            max_results=10,
        )
    )

    mock_download.assert_called_once_with(
        limit=200,
    )


@patch(
    "automation.sources.fmcsa.connector.download_company_sample"
)
def test_connector_limits_returned_companies(
    mock_download,
):
    mock_download.return_value = [
        build_record(f"Carrier {index}")
        for index in range(10)
    ]

    connector = FMCSAConnector()

    companies = connector.search(
        SearchFilters(
            max_results=3,
        )
    )

    assert len(companies) == 3


def test_connector_rejects_invalid_max_results():
    connector = FMCSAConnector()

    with pytest.raises(ValueError):
        connector.search(
            SearchFilters(
                max_results=0,
            )
        )