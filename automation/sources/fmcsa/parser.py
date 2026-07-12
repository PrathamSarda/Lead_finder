from typing import Any

from automation.models.company_lead import CompanyLead


def _clean_value(value: Any) -> str:
    """
    Convert a raw FMCSA value into a clean string.
    """

    if value is None:
        return ""

    return str(value).strip()


def _build_location(record: dict[str, Any]) -> str | None:
    """
    Build a readable city and state location.
    """

    city = _clean_value(record.get("phy_city"))
    state = _clean_value(record.get("phy_state"))

    if city and state:
        return f"{city}, {state}"

    return city or state or None


def _build_size_proxy(record: dict[str, Any]) -> str | None:
    """
    Build an operational-size description from FMCSA data.

    FMCSA does not provide a normal employee count, so driver
    and power-unit totals are retained as a source-specific proxy.
    """

    drivers = _clean_value(record.get("total_drivers"))
    power_units = _clean_value(record.get("power_units"))

    parts = []

    if drivers:
        parts.append(f"{drivers} drivers")

    if power_units:
        parts.append(f"{power_units} power units")

    if not parts:
        return None

    return ", ".join(parts)


def parse_company(record: dict[str, Any]) -> CompanyLead:
    """
    Convert one raw FMCSA record into a CompanyLead.
    """

    if not isinstance(record, dict):
        raise TypeError("FMCSA record must be a dictionary.")

    company_name = _clean_value(record.get("legal_name"))

    if not company_name:
        raise ValueError(
            "FMCSA record does not contain a legal company name."
        )

    return CompanyLead(
        company_name=company_name,
        website=None,
        industry=_clean_value(
            record.get("business_org_desc")
        ) or None,
        location=_build_location(record),
        employee_count=_build_size_proxy(record),
        contact_email=None,
        contact_phone=None,
        contact_page=None,
        source="FMCSA",
    )