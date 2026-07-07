from dataclasses import dataclass
from typing import Optional


@dataclass
class CompanyLead:
    company_name: str

    website: Optional[str] = None

    industry: Optional[str] = None

    location: Optional[str] = None

    employee_count: Optional[str] = None

    contact_email: Optional[str] = None

    contact_phone: Optional[str] = None

    contact_page: Optional[str] = None

    source: Optional[str] = None