from automation.models.company_lead import CompanyLead
from automation.sources.base_source import BaseSource
from automation.models.search_filters import SearchFilters


class GoogleSource(BaseSource):
    """
    Google Lead Source (Dummy Version)

    Returns sample data so that we can test the pipeline
    before implementing real scraping.
    """

    def search(self, filters: SearchFilters) -> list[CompanyLead]:

        print("Searching Google...")

        return [
            CompanyLead(
                company_name="ABC Software",
                website="https://abcsoftware.com",
                industry="Software",
                location="Texas, USA",
                employee_count="11-50",
                source="Google",
            ),
            CompanyLead(
                company_name="Bright Marketing",
                website="https://brightmarketing.com",
                industry="Marketing",
                location="California, USA",
                employee_count="1-10",
                source="Google",
            ),
        ]
