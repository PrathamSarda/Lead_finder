from typing import Any

import requests
from requests.exceptions import RequestException


FMCSA_DATASET_API_URL = (
    "https://data.transportation.gov/resource/az4n-8mr2.json"
)

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_SAMPLE_LIMIT = 10


class FMCSADownloadError(RuntimeError):
    """
    Raised when FMCSA data cannot be downloaded.
    """


def download_company_sample(
    limit: int = DEFAULT_SAMPLE_LIMIT,
    state: str | None = None,
    city: str | None = None,
) -> list[dict[str, Any]]:
    """
    Download a small sample from the FMCSA Company Census dataset.

    Args:
        limit:
            Maximum number of records to download.

    Returns:
        Raw FMCSA company records.

    Raises:
        ValueError:
            If limit is less than one.
        FMCSADownloadError:
            If the API request fails or returns invalid data.
    """

    if limit < 1:
        raise ValueError(
            "FMCSA sample limit must be at least 1."
        )

    try:
        params: dict[str, Any] = {"$limit": limit}
        clauses = ["status_code = 'A'"]
        if state:
            normalized_state = state.strip().upper()
            if len(normalized_state) != 2 or not normalized_state.isalpha():
                raise ValueError("State must be a two-letter US state code.")
            # Limit at the source so a state-filtered run does not sample unrelated rows.
            clauses.append(f"upper(phy_state) = '{normalized_state}'")
        if city and city.strip():
            safe_city = city.strip().replace("'", "''")[:100]
            clauses.append(f"upper(phy_city) = upper('{safe_city}')")
        params["$where"] = " AND ".join(clauses)
        response = requests.get(
            FMCSA_DATASET_API_URL,
            params=params,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except RequestException as exc:
        raise FMCSADownloadError(
            f"Unable to download FMCSA data: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise FMCSADownloadError(
            "FMCSA returned an invalid JSON response."
        ) from exc

    if not isinstance(payload, list):
        raise FMCSADownloadError(
            "FMCSA returned an unexpected response format."
        )

    return payload
