from typing import Any


ACTIVE_STATUS_CODE = "A"

US_COUNTRY_CODES = {
    "US",
    "USA",
    "UNITED STATES",
}

DEFAULT_MAX_DRIVERS = 20
DEFAULT_MAX_POWER_UNITS = 20


FLEET_SIZE_RANGES = {
    "0": (0, 0),
    "A": (1, 1),
    "B": (2, 3),
    "C": (4, 6),
    "D": (7, 8),
    "E": (9, 11),
    "F": (12, 14),
    "G": (15, 17),
    "H": (18, 19),
    "I": (20, 23),
    "J": (24, 28),
    "K": (29, 32),
    "L": (33, 38),
    "M": (39, 44),
    "N": (45, 55),
    "O": (56, 75),
    "P": (76, 100),
    "Q": (101, 200),
    "R": (201, 300),
    "S": (301, 400),
    "T": (401, 550),
    "U": (551, 999),
    "V": (1000, 2000),
    "W": (2001, 3000),
    "X": (3001, 4000),
    "Y": (4001, 5000),
    "Z": (5001, None),
}


def _parse_integer(value: Any) -> int | None:
    """
    Convert an FMCSA numeric value to an integer.

    Empty, malformed, and negative values return None.
    """

    if value is None:
        return None

    try:
        parsed_value = int(str(value).strip())
    except (TypeError, ValueError):
        return None

    if parsed_value < 0:
        return None

    return parsed_value


def is_active_company(record: dict[str, Any]) -> bool:
    """
    Return True when the FMCSA entity is active.
    """

    status_code = str(
        record.get("status_code", "")
    ).strip().upper()

    return status_code == ACTIVE_STATUS_CODE


def is_us_company(record: dict[str, Any]) -> bool:
    """
    Return True when the physical address is in the United States.

    Some FMCSA records omit the country while still providing a
    valid US state, so a two-letter state is accepted as a fallback.
    """

    country = str(
        record.get("phy_country", "")
    ).strip().upper()

    state = str(
        record.get("phy_state", "")
    ).strip().upper()

    if country in US_COUNTRY_CODES:
        return True

    return len(state) == 2 and state.isalpha()


def has_required_identity(record: dict[str, Any]) -> bool:
    """
    Check whether a record has enough identity data to become a lead.
    """

    company_name = str(
        record.get("legal_name", "")
    ).strip()

    city = str(
        record.get("phy_city", "")
    ).strip()

    state = str(
        record.get("phy_state", "")
    ).strip()

    return bool(company_name and (city or state))


def is_small_operator(
    record: dict[str, Any],
    max_drivers: int = DEFAULT_MAX_DRIVERS,
    max_power_units: int = DEFAULT_MAX_POWER_UNITS,
) -> bool:
    """
    Determine whether an FMCSA entity is a small operator.

    Exact driver and power-unit totals are preferred. Fleet-size
    code is used only when power_units is unavailable.
    """

    if max_drivers < 1:
        raise ValueError(
            "Maximum drivers must be at least 1."
        )

    if max_power_units < 1:
        raise ValueError(
            "Maximum power units must be at least 1."
        )

    drivers = _parse_integer(
        record.get("total_drivers")
    )

    power_units = _parse_integer(
        record.get("power_units")
    )

    if drivers is not None and drivers > max_drivers:
        return False

    if (
        power_units is not None
        and power_units > max_power_units
    ):
        return False

    if drivers is not None or power_units is not None:
        return True

    fleet_code = str(
        record.get("fleetsize", "")
    ).strip().upper()

    fleet_range = FLEET_SIZE_RANGES.get(fleet_code)

    if fleet_range is None:
        return False

    fleet_minimum, _ = fleet_range

    return fleet_minimum <= max_power_units


def is_qualified_company(
    record: dict[str, Any],
    max_drivers: int = DEFAULT_MAX_DRIVERS,
    max_power_units: int = DEFAULT_MAX_POWER_UNITS,
) -> bool:
    """
    Apply the complete FMCSA lead-qualification policy.
    """

    return (
        is_active_company(record)
        and is_us_company(record)
        and has_required_identity(record)
        and is_small_operator(
            record=record,
            max_drivers=max_drivers,
            max_power_units=max_power_units,
        )
    )


def filter_company_records(
    records: list[dict[str, Any]],
    max_drivers: int = DEFAULT_MAX_DRIVERS,
    max_power_units: int = DEFAULT_MAX_POWER_UNITS,
) -> list[dict[str, Any]]:
    """
    Return only qualified FMCSA company records.
    """

    return [
        record
        for record in records
        if is_qualified_company(
            record=record,
            max_drivers=max_drivers,
            max_power_units=max_power_units,
        )
    ]
