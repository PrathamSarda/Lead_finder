"""
Pydantic schemas for Company (lead) request/response validation.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    location: str | None = None
    employee_count: int | None = None


class CompanyCreate(CompanyBase):
    sources: list[str] | None = None


class CompanyUpdate(BaseModel):
    website: str | None = None
    industry: str | None = None
    location: str | None = None
    employee_count: int | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    status: str | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sources: list[str] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    status: str
    created_at: datetime
