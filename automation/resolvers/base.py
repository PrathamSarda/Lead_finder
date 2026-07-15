from abc import ABC, abstractmethod

from automation.models.website_resolution_result import (
    WebsiteResolutionResult,
)


class WebsiteResolver(ABC):
    """
    Contract implemented by all website resolvers.
    """

    @abstractmethod
    def resolve(
        self,
        company_name: str,
        location: str | None = None,
    ) -> WebsiteResolutionResult:
        """
        Resolve the most likely official company website.
        """
