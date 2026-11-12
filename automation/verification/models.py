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


class LeadTier(str, Enum):
    FULL_LEAD = "FULL_LEAD"                    # Verified website + verified direct contact (email and/or phone)
    WEBSITE_ONLY = "WEBSITE_ONLY"              # Verified website only (no verified direct email/phone)
    DIRECTORY_CONTACT = "DIRECTORY_CONTACT"    # No custom website, but direct contact found via official FMCSA/DOT directory
    UNRESOLVED = "UNRESOLVED"                  # No verified website and no contacts


EXPORT_FIELDNAMES = [
    "company_name",
    "location",
    "status",
    "lead_tier",
    "status_reason",
    "website",
    "website_status",
    "website_source",
    "email",
    "email_status",
    "email_source",
    "decision_maker_name",
    "decision_maker_title",
    "decision_maker_linkedin_url",
    "has_recent_linkedin_post",
    "email_confidence",
    "phone",
    "phone_status",
    "phone_source",
    "confidence",
    "source",
    "candidate_results",
    "elapsed_seconds",
    "created_at",
]


@dataclass(slots=True)
class VerifiedLead:
    """
    Final representation of a verified company lead with field-level verification and provenance.
    """
    company_name: str
    location: str
    status: str
    status_reason: str
    lead_tier: str = "UNRESOLVED"
    website: str | None = None
    website_status: str = "UNRESOLVED"
    website_source: str | None = None
    email: str | None = None
    email_status: str = "UNRESOLVED"
    email_source: str | None = None
    phone: str | None = None
    phone_status: str = "UNRESOLVED"
    phone_source: str | None = None
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    candidate_results: list[dict[str, str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, object]:
        import json
        clean_candidates = ""
        if self.candidate_results:
            clean_candidates = json.dumps(self.candidate_results, ensure_ascii=True).replace("\r", " ").replace("\n", " ")

        return {
            "company_name": str(self.company_name or ""),
            "location": str(self.location or ""),
            "status": str(self.status or "UNRESOLVED"),
            "lead_tier": str(self.lead_tier or "UNRESOLVED"),
            "status_reason": str(self.status_reason or ""),
            "website": str(self.website or ""),
            "website_status": str(self.website_status or "UNRESOLVED"),
            "website_source": str(self.website_source or ""),
            "email": str(self.email or ""),
            "email_status": str(self.email_status or "UNRESOLVED"),
            "email_source": str(self.email_source or ""),
            "phone": str(self.phone or ""),
            "phone_status": str(self.phone_status or "UNRESOLVED"),
            "phone_source": str(self.phone_source or ""),
            "confidence": round(float(self.confidence or 0.0), 2),
            "source": ", ".join(self.sources) if self.sources else "",
            "candidate_results": clean_candidates,
            "elapsed_seconds": round(float(self.elapsed_seconds or 0.0), 2),
            "created_at": str(self.created_at or ""),
        }
