"""
Data models for lead verification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNRESOLVED = "UNRESOLVED"


@dataclass(slots=True)
class VerifiedLead:
    """
    Final representation of a verified company lead with provenance tracking.
    """
    company_name: str
    location: str
    status: str
    status_reason: str
    website: str | None = None
    website_source: str | None = None
    email: str | None = None
    email_source: str | None = None
    phone: str | None = None
    phone_source: str | None = None
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "company_name": self.company_name,
            "location": self.location,
            "status": self.status,
            "status_reason": self.status_reason,
            "website": self.website or "",
            "website_source": self.website_source or "",
            "email": self.email or "",
            "email_source": self.email_source or "",
            "phone": self.phone or "",
            "phone_source": self.phone_source or "",
            "confidence": self.confidence,
            "source": ", ".join(self.sources) if self.sources else "",
            "elapsed_seconds": self.elapsed_seconds,
            "created_at": self.created_at,
        }
