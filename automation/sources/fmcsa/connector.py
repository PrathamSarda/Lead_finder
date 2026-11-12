from automation.models.company_lead import CompanyLead
from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.downloader import (
    download_company_sample,
)
from automation.sources.fmcsa.filters import (
    filter_company_records,
    has_required_identity,
    is_active_company,
    is_us_company,
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

    def search_candidates(self, filters: SearchFilters) -> list[CompanyLead]:
        """Return active US FMCSA entities for downstream LinkedIn headcount qualification.

        This intentionally does not apply the driver/power-unit size proxy: the
        workflow's definitive size gate is the LinkedIn employee count.
        """
        if filters.max_results < 1:
            raise ValueError("SearchFilters.max_results must be at least 1.")
        raw_limit = min(max(filters.max_results * DEFAULT_RAW_RECORD_MULTIPLIER, 100), MAX_RAW_RECORDS)
        raw_records = download_company_sample(limit=raw_limit, state=filters.state, city=filters.city)
        eligible = [r for r in raw_records if is_active_company(r) and is_us_company(r) and has_required_identity(r)]
        return [parse_company(record) for record in eligible[:filters.max_results]]
