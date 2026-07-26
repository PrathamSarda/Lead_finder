from automation.intelligence.company_pipeline import CompanyPipeline
from automation.intelligence.models import CompanyInput
from automation.resolvers.providers.base import SearchResult


class FakeSearchEngine:

    def search(
        self,
        query: str,
    ):

        if "linkedin" in query:

            return [
                SearchResult(
                    title="Brockman Trucking Inc",
                    url="https://www.linkedin.com/company/brockman-trucking-inc",
                    snippet=(
                        "Website: https://brockmantrailers.com "
                        "Transportation company."
                    ),
                    provider="fake",
                    position=1,
                )
            ]

        if "official website" in query:

            return [
                SearchResult(
                    title="Brockman Trucking",
                    url="https://brockmantrailers.com",
                    snippet=(
                        "Email info@brockmantrailers.com "
                        "Phone (651) 555-1234"
                    ),
                    provider="fake",
                    position=1,
                )
            ]

        return []

def test_pipeline_runs_end_to_end():

        pipeline = CompanyPipeline(
            search_engine=FakeSearchEngine(),
        )

        company = CompanyInput(
            name="BROCKMAN TRUCKING INC",
            city="Afton",
            state="MN",
        )

        merged = pipeline.run(company)

        assert merged is not None

        assert merged.company_name == "Brockman Trucking Inc"

        assert merged.website == "https://brockmantrailers.com"

        assert "linkedin" in merged.sources