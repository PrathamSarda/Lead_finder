"""
Pydantic schemas for Company lead request and response validation.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    website: str | None = None
    industry: str | None = None
    location: str | None = None

    # Job websites commonly return ranges such as "1-10" or "11-50",
    # rather than an exact employee count.
    employee_count: str | None = None


class CompanyCreate(CompanyBase):
    sources: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_page: str | None = None
    status: str = "new"
    raw_data: dict[str, Any] | None = None


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    website: str | None = None
    industry: str | None = None
    location: str | None = None
    employee_count: str | None = None
    sources: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_page: str | None = None
    status: str | None = None
    raw_data: dict[str, Any] | None = None
    last_seen: datetime | None = None
    notes: str | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sources: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_page: str | None = None
    status: str
    raw_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    last_seen: datetime | None = None
    notes: str | None = None