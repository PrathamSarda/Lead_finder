from automation.models.company_lead import CompanyLead
from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.downloader import (
    download_company_sample,
)
from automation.sources.fmcsa.filters import (
    filter_company_records,
)
from automation.sources.fmcsa.parser import parse_company


DEFAULT_RAW_RECORD_MULTIPLIER = 20
MAX_RAW_RECORDS = 5_000


class FMCSAConnector:
    """
    Official FMCSA lead-source connector.

    The connector downloads more raw records than requested because
    inactive, foreign, incomplete, and large operators are filtered out
    before CompanyLead objects are returned.
    """

    def search(
        self,
        filters: SearchFilters,
    ) -> list[CompanyLead]:
        """
        Return up to filters.max_results qualified FMCSA companies.
        """

        if filters.max_results < 1:
            raise ValueError(
                "SearchFilters.max_results must be at least 1."
            )

        raw_limit = min(
            filters.max_results
            * DEFAULT_RAW_RECORD_MULTIPLIER,
            MAX_RAW_RECORDS,
        )

        raw_records = download_company_sample(
            limit=raw_limit,
        )

        qualified_records = filter_company_records(
            raw_records,
        )

        companies = [
            parse_company(record)
            for record in qualified_records
        ]

        return companies[:filters.max_results]