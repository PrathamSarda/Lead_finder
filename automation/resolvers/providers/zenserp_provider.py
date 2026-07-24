from __future__ import annotations
from urllib import response
from wsgiref import headers
from dotenv import load_dotenv
from fastapi import params

load_dotenv()

import os
from typing import Any

import requests

from automation.resolvers.providers.base import (
    SearchProvider,
    SearchProviderError,
    SearchResult,
)


DEFAULT_ZENSERP_ENDPOINT = (
    "https://app.zenserp.com/api/v2/search"
)


class ZenserpProvider(SearchProvider):
    """
    Search provider backed by the Zenserp Search API.

    This class is responsible only for:

    - sending a search query to Zenserp;
    - parsing organic search results;
    - converting results into SearchResult objects.

    Filtering, scoring, homepage validation, and final website
    selection belong to WebsiteResolver.
    """

    name = "zenserp"

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = DEFAULT_ZENSERP_ENDPOINT,
        timeout: float = 15.0,
        max_results: int = 10,
        country_code: str = "us",
        language: str = "en",
        session: requests.Session | None = None,
    ) -> None:
        """
        Initialize the Zenserp provider.

        Args:
            api_key:
                Zenserp API key. When omitted, the provider reads
                ZENSERP_API_KEY from the environment.

            endpoint:
                Zenserp search endpoint.

            timeout:
                HTTP request timeout in seconds.

            max_results:
                Maximum number of organic results requested and returned
                for each query.

            country_code:
                Search country code, such as "us".

            language:
                Search result language, such as "en".

            session:
                Optional requests.Session for testing or connection reuse.
        """

        resolved_api_key = (
            api_key or os.getenv("ZENSERP_API_KEY", "")
        ).strip()

        if not resolved_api_key:
            raise ValueError(
                "Zenserp API key is missing. Set the "
                "ZENSERP_API_KEY environment variable or pass "
                "api_key= when creating ZenserpProvider."
            )

        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero."
            )

        if max_results <= 0:
            raise ValueError(
                "max_results must be greater than zero."
            )

        self.api_key = resolved_api_key
        self.endpoint = endpoint.strip()
        self.timeout = timeout
        self.max_results = max_results
        self.country_code = country_code.strip().lower()
        self.language = language.strip().lower()
        self.session = session or requests.Session()
        print("Session:", type(self.session))
        print("Verify:", self.session.verify)
        print("Endpoint:", self.endpoint)

        if not self.endpoint:
            raise ValueError(
                "Zenserp endpoint cannot be empty."
            )

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        """
        Search Zenserp and return normalized organic results.

        Raises:
            SearchProviderError:
                When the request fails, Zenserp rejects the request,
                the response is malformed, or an API error is returned.
        """

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Search query cannot be empty."
            )

        payload = self._request_search(
            normalized_query
        )
        print("\nZenserp payload type:", type(payload))
        print("Zenserp payload keys:", list(payload.keys()))

        organic_results = payload.get("organic")

        if organic_results is None:
            organic_results = payload.get("organic_results")

        if organic_results is None:
            data = payload.get("data", {})

            if isinstance(data, dict):
                organic_results = (
                    data.get("organic")
                    or data.get("organic_results")
                )

        if not isinstance(organic_results, list):
            organic_results = []
        print("Organic type:", type(organic_results))
        print(
            "Organic count:",
            len(organic_results) if isinstance(organic_results, list) else "not a list",
        )

        print(
            "Payload preview:",
            str(payload)[:2000],
        )
        return self._parse_organic_results(
            payload=payload,
        )

    def _request_search(
        self,
        query: str,
    ) -> dict[str, Any]:
        """
        Execute one Zenserp API request.
        """

        headers = {
            "apikey": self.api_key,
            "Accept": "application/json",
            "User-Agent": (
                "CompanyLeadFinder/1.0 "
                "(ZenserpProvider)"
            ),
        }

        params: dict[str, str | int] = {
            "q": query,
            "num": self.max_results,
        }

        if self.country_code:
            params["gl"] = self.country_code

        if self.language:
            params["hl"] = self.language

        print("Request URL:", self.endpoint)

        safe_headers = {
            **headers,
            "apikey": "***",
        }

        print("Headers:", safe_headers)
        print("Params:", params)
        try:
            response = requests.get(
    self.endpoint,
    headers=headers,
    params=params,
    timeout=self.timeout,
)

        except requests.Timeout as exc:
            raise SearchProviderError(
                "Zenserp request timed out for query "
                f"{query!r}."
            ) from exc

        except requests.ConnectionError as exc:
            raise SearchProviderError(
                "Could not connect to Zenserp for query "
                f"{query!r}."
            ) from exc

        except requests.RequestException as exc:
            raise SearchProviderError(
                "Zenserp request failed for query "
                f"{query!r}: {exc}"
            ) from exc

        if response.status_code in {
            401,
            403,
        }:
            print("Status Code:", response.status_code)
            print("Response Body:", response.text)
            raise SearchProviderError(
                "Zenserp authentication failed. Check the "
                "ZENSERP_API_KEY value and account access."
            )

        if response.status_code == 429:
            raise SearchProviderError(
                "Zenserp rate limit or request quota was reached."
            )

        if not response.ok:
            response_message = self._response_preview(
                response
            )

            raise SearchProviderError(
                "Zenserp returned HTTP "
                f"{response.status_code}: {response_message}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SearchProviderError(
                "Zenserp returned a non-JSON response."
            ) from exc

        if not isinstance(payload, dict):
            raise SearchProviderError(
                "Zenserp returned an unexpected response format."
            )

        self._raise_for_api_error(payload)

        return payload

    def _parse_organic_results(
        self,
        payload: dict[str, Any],
    ) -> list[SearchResult]:
        """
        Convert Zenserp organic results to SearchResult objects.
        """

        organic_results = payload.get(
            "organic",
            []
        )

        if organic_results is None:
            return []

        if not isinstance(organic_results, list):
            raise SearchProviderError(
                "Zenserp response field 'organic' was not a list."
            )

        normalized_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for fallback_position, item in enumerate(
            organic_results,
            start=1,
        ):
            if len(normalized_results) >= self.max_results:
                break

            if not isinstance(item, dict):
                continue

            url = self._extract_url(item)

            if not url:
                continue

            normalized_identity = url.strip().lower()

            if normalized_identity in seen_urls:
                continue

            seen_urls.add(normalized_identity)

            title = self._safe_string(
                item.get("title")
            )

            snippet = self._extract_snippet(item)

            position = self._safe_position(
                item.get("position"),
                fallback=fallback_position,
            )

            normalized_results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider=self.name,
                    position=position,
                )
            )

        return normalized_results

    @staticmethod
    def _extract_url(
        item: dict[str, Any],
    ) -> str:
        """
        Extract a destination URL from a Zenserp result.

        Different response versions may expose the destination using
        slightly different keys.
        """

        possible_values = (
            item.get("url"),
            item.get("link"),
            item.get("destination"),
        )

        for value in possible_values:
            if isinstance(value, str):
                normalized_value = value.strip()

                if normalized_value:
                    return normalized_value

        return ""

    @staticmethod
    def _extract_snippet(
        item: dict[str, Any],
    ) -> str:
        """
        Extract result summary text.
        """

        possible_values = (
            item.get("description"),
            item.get("snippet"),
            item.get("text"),
        )

        for value in possible_values:
            if isinstance(value, str):
                normalized_value = value.strip()

                if normalized_value:
                    return normalized_value

        return ""

    @staticmethod
    def _safe_string(
        value: Any,
    ) -> str:
        """
        Safely convert an API value to a clean string.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    @staticmethod
    def _safe_position(
        value: Any,
        fallback: int,
    ) -> int:
        """
        Safely parse a search-result position.
        """

        if isinstance(value, bool):
            return fallback

        if isinstance(value, int):
            return max(value, 1)

        if isinstance(value, float):
            return max(int(value), 1)

        if isinstance(value, str):
            try:
                return max(
                    int(float(value.strip())),
                    1,
                )
            except (
                TypeError,
                ValueError,
            ):
                return fallback

        return fallback

    @staticmethod
    def _raise_for_api_error(
        payload: dict[str, Any],
    ) -> None:
        """
        Detect API-level errors returned inside a successful HTTP response.
        """

        error_value = payload.get("error")

        if not error_value:
            return

        if isinstance(error_value, str):
            message = error_value.strip()

        elif isinstance(error_value, dict):
            message = (
                error_value.get("message")
                or error_value.get("description")
                or error_value.get("code")
                or str(error_value)
            )

        else:
            message = str(error_value)

        raise SearchProviderError(
            f"Zenserp API error: {message}"
        )

    @staticmethod
    def _response_preview(
        response: requests.Response,
        limit: int = 300,
    ) -> str:
        """
        Return a short response body for error diagnostics without
        exposing an excessive response.
        """

        try:
            text = response.text.strip()
        except Exception:
            return "No response details available."

        if not text:
            return "No response details available."

        if len(text) > limit:
            return f"{text[:limit]}..."

        return text
