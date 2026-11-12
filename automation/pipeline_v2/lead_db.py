"""
Persistent SQLite Lead Storage & Deduplication Manager.
Stores every discovered business and verified lead.
Prevents duplicate outreach within a configurable cooldown period (e.g. 15-20 days).
Allows fresh leads every single run, while recycling after the cooldown window.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize_name(name: str) -> str:
    """Normalize company name for fuzzy duplicate comparison (removes LLC, Inc, Corp, punctuation)."""
    if not name:
        return ""
    n = name.lower()
    # Strip common business suffixes
    n = re.sub(r"\b(llc|inc|corp|co|company|ltd|services|enterprises|group)\b", "", n)
    # Remove non-alphanumeric chars
    n = re.sub(r"[^a-z0-9]", "", n)
    return n.strip()


def _normalize_domain(domain: str | None) -> str:
    """Normalize web domain (lowercase, strip www and protocol)."""
    if not domain:
        return ""
    d = domain.lower().strip()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    return d.split("/")[0].strip()


class LeadDatabase:
    """Persistent SQLite database tracking all discovered and contacted companies."""

    DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "leads_history.db"

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    domain TEXT,
                    normalized_domain TEXT,
                    website TEXT,
                    phone TEXT,
                    address TEXT,
                    category TEXT,
                    employee_count TEXT,
                    company_linkedin_url TEXT,
                    owner_name TEXT,
                    owner_title TEXT,
                    decision_maker_linkedin_url TEXT,
                    owner_email TEXT,
                    status TEXT DEFAULT 'DISCOVERED',
                    confidence REAL DEFAULT 0.0,
                    source TEXT,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    run_count INTEGER DEFAULT 1
                );
                """
            )
            # Gracefully ensure new columns exist in pre-existing database tables
            for col in (
                "company_linkedin_url",
                "decision_maker_linkedin_url",
                "intent_source",
                "indeed_job_url",
                "company_email",
                "decision_maker_email",
                "region",
                "after_date",
            ):
                try:
                    cursor.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT;")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_norm_domain ON companies(normalized_domain);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_norm_name ON companies(normalized_name);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_last_processed ON companies(last_processed_at);"
            )
            conn.commit()

    def is_recent_duplicate(
        self,
        company_name: str,
        domain: Optional[str] = None,
        cooldown_days: int = 18,
        only_qualified: bool = True,
    ) -> bool:
        """
        Check if a company has been processed within the cooldown window (default 18 days).
        only_qualified=True ensures we skip only companies that were previously verified/qualified,
        so any company that had an unverified attempt or temporary lookup issue is not permanently blocked.
        """
        norm_name = _normalize_name(company_name)
        norm_dom = _normalize_domain(domain)
        cutoff_date = datetime.now() - timedelta(days=cooldown_days)
        cutoff_iso = cutoff_date.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if only_qualified:
                query = """
                    SELECT id, company_name, last_processed_at 
                    FROM companies 
                    WHERE (
                        (normalized_domain != '' AND normalized_domain = ?)
                        OR (normalized_name != '' AND normalized_name = ?)
                    )
                    AND last_processed_at > ?
                    AND status = 'QUALIFIED_CONVERTIBLE'
                    LIMIT 1
                """
            else:
                query = """
                    SELECT id, company_name, last_processed_at 
                    FROM companies 
                    WHERE (
                        (normalized_domain != '' AND normalized_domain = ?)
                        OR (normalized_name != '' AND normalized_name = ?)
                    )
                    AND last_processed_at > ?
                    LIMIT 1
                """
            cursor.execute(query, (norm_dom, norm_name, cutoff_iso))
            row = cursor.fetchone()
            return row is not None

    def record_lead(
        self,
        company_name: str,
        domain: Optional[str] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        category: Optional[str] = None,
        employee_count: Optional[str] = None,
        company_linkedin_url: Optional[str] = None,
        owner_name: Optional[str] = None,
        owner_title: Optional[str] = None,
        decision_maker_linkedin_url: Optional[str] = None,
        owner_email: Optional[str] = None,
        company_email: Optional[str] = None,
        decision_maker_email: Optional[str] = None,
        region: Optional[str] = None,
        after_date: Optional[str] = None,
        status: str = "QUALIFIED_CONVERTIBLE",
        confidence: float = 0.0,
        source: Optional[str] = None,
    ) -> None:
        """Insert or update a company record with current timestamp and contact info."""
        norm_name = _normalize_name(company_name)
        norm_dom = _normalize_domain(domain or website)
        now_iso = datetime.now().isoformat()
        dm_email = decision_maker_email or owner_email

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check existing
            cursor.execute(
                """
                SELECT id, run_count FROM companies
                WHERE (normalized_domain != '' AND normalized_domain = ?)
                   OR (normalized_name != '' AND normalized_name = ?)
                LIMIT 1
                """,
                (norm_dom, norm_name),
            )
            existing = cursor.fetchone()

            if existing:
                lead_id, run_cnt = existing["id"], existing["run_count"]
                cursor.execute(
                    """
                    UPDATE companies
                    SET company_name = ?,
                        domain = COALESCE(?, domain),
                        website = COALESCE(?, website),
                        phone = COALESCE(?, phone),
                        address = COALESCE(?, address),
                        category = COALESCE(?, category),
                        employee_count = COALESCE(?, employee_count),
                        company_linkedin_url = COALESCE(?, company_linkedin_url),
                        owner_name = COALESCE(?, owner_name),
                        owner_title = COALESCE(?, owner_title),
                        decision_maker_linkedin_url = COALESCE(?, decision_maker_linkedin_url),
                        owner_email = COALESCE(?, owner_email),
                        company_email = COALESCE(?, company_email),
                        decision_maker_email = COALESCE(?, decision_maker_email),
                        region = COALESCE(?, region),
                        after_date = COALESCE(?, after_date),
                        status = ?,
                        confidence = MAX(confidence, ?),
                        source = COALESCE(?, source),
                        last_processed_at = ?,
                        run_count = ?
                    WHERE id = ?
                    """,
                    (
                        company_name,
                        domain,
                        website,
                        phone,
                        address,
                        category,
                        str(employee_count) if employee_count else None,
                        company_linkedin_url,
                        owner_name,
                        owner_title,
                        decision_maker_linkedin_url,
                        dm_email,
                        company_email,
                        dm_email,
                        region,
                        after_date,
                        status,
                        confidence,
                        source,
                        now_iso,
                        run_cnt + 1,
                        lead_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO companies (
                        company_name, normalized_name, domain, normalized_domain, website,
                        phone, address, category, employee_count, company_linkedin_url,
                        owner_name, owner_title, decision_maker_linkedin_url, owner_email,
                        company_email, decision_maker_email, region, after_date,
                        status, confidence, source, first_seen_at, last_processed_at, run_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        company_name,
                        norm_name,
                        domain,
                        norm_dom,
                        website,
                        phone,
                        address,
                        category,
                        str(employee_count) if employee_count else None,
                        company_linkedin_url,
                        owner_name,
                        owner_title,
                        decision_maker_linkedin_url,
                        dm_email,
                        company_email,
                        dm_email,
                        region,
                        after_date,
                        status,
                        confidence,
                        source,
                        now_iso,
                        now_iso,
                    ),
                )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Return total saved companies, contacts found, and recently processed counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM companies")
            total = cursor.fetchone()["total"]

            cursor.execute(
                "SELECT COUNT(*) as with_email FROM companies WHERE owner_email IS NOT NULL AND owner_email != ''"
            )
            with_email = cursor.fetchone()["with_email"]

            cursor.execute(
                "SELECT COUNT(*) as with_phone FROM companies WHERE phone IS NOT NULL AND phone != ''"
            )
            with_phone = cursor.fetchone()["with_phone"]

            return {
                "total_companies_stored": total,
                "companies_with_email": with_email,
                "companies_with_phone": with_phone,
            }
