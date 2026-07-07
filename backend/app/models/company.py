"""
Company (lead) model.

Represents a candidate company discovered by the automation pipeline —
distinct from `User`, which is the app's own login/account model.

Minimal fields for the lead-finding use case. Extend as enrichment and
outreach-tracking needs grow (e.g. outreach status, notes, assigned owner).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # US state/city — kept as free text for now; normalize later if needed.
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    employee_count: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Which source(s) surfaced this company, e.g. ["linkedin", "google"].
    sources: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    contact_page: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True
)
    # Lifecycle: new -> enriched -> contact_found -> contacted, etc.
    # Left as free text rather than an enum so the workflow can evolve
    # without a migration for each new status.
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)

    # Raw per-source data for debugging/audit (e.g. what each source returned).
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_seen: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True
)
    notes: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
)
