from dataclasses import dataclass
from typing import Optional


@dataclass
class ContactInfo:
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_page: Optional[str] = None