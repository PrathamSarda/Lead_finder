from abc import ABC, abstractmethod
from typing import List

from automation.models.search_filters import SearchFilters
from automation.models.company_lead import CompanyLead


class BaseSource(ABC):
    """
    Abstract base class for all lead sources.
    """

    @abstractmethod
    def search(self, filters: SearchFilters) -> List[CompanyLead]:
        """
        Search for companies and return normalized CompanyLead objects.
        """
        pass