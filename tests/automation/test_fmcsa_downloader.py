from unittest.mock import Mock, patch

import pytest
import requests

from automation.sources.fmcsa.downloader import (
    FMCSADownloadError,
    download_company_sample,
)


def test_download_company_sample_rejects_invalid_limit():
    with pytest.raises(ValueError):
        download_company_sample(limit=0)


@patch(
    "automation.sources.fmcsa.downloader.requests.get"
)
def test_download_company_sample_returns_records(
    mock_get,
):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "legal_name": "Example Logistics LLC",
            "phy_state": "OH",
        }
    ]

    mock_get.return_value = response

    records = download_company_sample(limit=1)

    assert records == [
        {
            "legal_name": "Example Logistics LLC",
            "phy_state": "OH",
        }
    ]

    mock_get.assert_called_once()


@patch(
    "automation.sources.fmcsa.downloader.requests.get"
)
def test_download_company_sample_wraps_request_errors(
    mock_get,
):
    mock_get.side_effect = requests.RequestException(
        "Network unavailable"
    )

    with pytest.raises(FMCSADownloadError):
        download_company_sample(limit=10)


@patch(
    "automation.sources.fmcsa.downloader.requests.get"
)
def test_download_company_sample_rejects_non_list_response(
    mock_get,
):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "error": "Unexpected response"
    }

    mock_get.return_value = response

    with pytest.raises(FMCSADownloadError):
        download_company_sample(limit=10)