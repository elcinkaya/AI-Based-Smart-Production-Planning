"""
analysis.py – Production performance (KPI) calculations for production records.

This module computes the plan-vs-actual gap and simple performance
indicators from ProductionRecord objects, following Section 3.4 of the
project plan:

    production_gap   = actual_units - planned_units
                       (positive: over-production, negative: shortfall, 0: exact)
    attainment_pct   = actual_units / planned_units * 100
    availability_pct = (record_count * 8 - total_downtime_hours)
                       / (record_count * 8) * 100
    plan_met         = total_actual_units >= total_planned_units

Numbers are NEVER rounded here; rounding happens only in report.py.
No print or input is used in this module.

Author: Kişi C
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

from typing import Any

from factory_model.base import validate_number
from production_records.record import SHIFT_HOURS, ProductionRecord, Shift


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Record fields that summarize_by() accepts as a grouping key.
GROUP_FIELDS: tuple[str, ...] = (
    "production_date",
    "machine_id",
    "product_code",
    "shift",
)

#: Keys of the summary dictionary (Section 3.4), in contract order.
SUMMARY_KEYS: tuple[str, ...] = (
    "record_count",
    "date_from",
    "date_to",
    "total_planned_units",
    "total_actual_units",
    "production_gap",
    "attainment_pct",
    "total_downtime_hours",
    "availability_pct",
    "plan_met",
    "status_message",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_units(value: Any, field_name: str) -> int:
    """Validate a unit count: a non-negative int (bool and float rejected).

    Args:
        value: The value to validate.
        field_name: Field name used in the Turkish error message.

    Returns:
        The validated integer.

    Raises:
        TypeError: If *value* is not an int (bool is rejected).
        ValueError: If *value* is negative.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} tam sayı (int) olmalıdır.")
    if value < 0:
        raise ValueError(f"{field_name} negatif olamaz.")
    return value


def _validate_record_list(records: Any) -> list[ProductionRecord]:
    """Validate that *records* is a non-empty list of ProductionRecord objects.

    Args:
        records: The value to validate.

    Returns:
        The same list.

    Raises:
        TypeError: If *records* is not a list or contains a non-record item.
        ValueError: If *records* is empty.
    """
    if not isinstance(records, list):
        raise TypeError("Kayıtlar bir liste (list) olarak verilmelidir.")
    if not records:
        raise ValueError("Özet hesaplamak için en az bir kayıt gereklidir.")
    for idx, rec in enumerate(records):
        if not isinstance(rec, ProductionRecord):
            raise TypeError(
                f"Kayıt listesinin {idx}. elemanı ProductionRecord türünde olmalıdır."
            )
    return records


def _build_status_message(production_gap: int) -> str:
    """Return the Turkish status message for a total production gap.

    Args:
        production_gap: total_actual_units - total_planned_units.

    Returns:
        The status message defined in Section 3.4.
    """
    if production_gap > 0:
        return f"Plan karşılandı. Fazla üretim: {production_gap} adet."
    if production_gap == 0:
        return "Plan tam olarak gerçekleşti."
    return f"Plan karşılanmadı. Üretim açığı: {abs(production_gap)} adet."


def _group_value(record: ProductionRecord, group_field: str) -> str:
    """Return the grouping value of *record* as it appears in to_dict().

    Dates are returned as ISO text and shifts as their string value, so
    group keys match the file representation (e.g. '2026-10-01', 'morning').
    """
    return record.to_dict()[group_field]


def _group_sort_key(group_field: str, value: str) -> tuple[int, str]:
    """Sort key for group values: shifts follow enum order, others are sorted."""
    if group_field == "shift":
        order = [s.value for s in Shift]
        return (order.index(value), value)
    return (0, value)


# ---------------------------------------------------------------------------
# Single KPI functions
# ---------------------------------------------------------------------------

def calculate_production_gap(planned_units: int, actual_units: int) -> int:
    """Calculate the production gap (actual - planned).

    Sign convention (same as MP1 capacity_gap): positive means
    over-production, negative means a production shortfall, 0 means the
    plan was met exactly.

    Args:
        planned_units: Planned quantity in units (int >= 0).
        actual_units: Actual quantity in units (int >= 0).

    Returns:
        actual_units - planned_units, in units.

    Raises:
        TypeError: If an argument is not an int (bool is rejected).
        ValueError: If an argument is negative.
    """
    planned = _validate_units(planned_units, "Planlanan miktar (planned_units)")
    actual = _validate_units(actual_units, "Gerçekleşen miktar (actual_units)")
    return actual - planned


def calculate_attainment_pct(planned_units: int, actual_units: int) -> float:
    """Calculate plan attainment as a percentage (actual / planned * 100).

    Args:
        planned_units: Planned quantity in units (int > 0).
        actual_units: Actual quantity in units (int >= 0).

    Returns:
        Attainment percentage (not rounded).

    Raises:
        TypeError: If an argument is not an int (bool is rejected).
        ValueError: If planned_units <= 0 or actual_units < 0.
    """
    if isinstance(planned_units, bool) or not isinstance(planned_units, int):
        raise TypeError("Planlanan miktar (planned_units) tam sayı (int) olmalıdır.")
    if planned_units <= 0:
        raise ValueError("Planlanan miktar (planned_units) sıfırdan büyük olmalıdır.")
    actual = _validate_units(actual_units, "Gerçekleşen miktar (actual_units)")
    return actual / planned_units * 100


def calculate_availability_pct(
    downtime_hours: float, shift_hours: float = SHIFT_HOURS
) -> float:
    """Calculate availability as a percentage of the scheduled time.

    Formula: (shift_hours - downtime_hours) / shift_hours * 100

    For a set of records, pass the total downtime and
    ``record_count * SHIFT_HOURS`` as *shift_hours*; this gives the
    Section 3.4 formula
    ``(record_count * 8 - total_downtime) / (record_count * 8) * 100``.

    Args:
        downtime_hours: Downtime in hours (0 <= x <= shift_hours).
        shift_hours: Scheduled time in hours (x > 0). Defaults to one
            shift (SHIFT_HOURS = 8.0).

    Returns:
        Availability percentage (not rounded).

    Raises:
        TypeError: If an argument is not numeric (bool is rejected).
        ValueError: If shift_hours <= 0 or downtime_hours is outside
            [0, shift_hours].
    """
    scheduled = validate_number(
        shift_hours, "Planlı çalışma süresi (shift_hours)",
        lower=0.0, lower_inclusive=False,
    )
    downtime = validate_number(
        downtime_hours, "Duruş süresi (downtime_hours)",
        lower=0.0, upper=scheduled,
    )
    return (scheduled - downtime) / scheduled * 100


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def summarize_records(records: list) -> dict:
    """Build the KPI summary dictionary (Section 3.4) for a list of records.

    Args:
        records: Non-empty list of ProductionRecord objects.

    Returns:
        Dictionary with keys: record_count (int), date_from (str, ISO),
        date_to (str, ISO), total_planned_units (int),
        total_actual_units (int), production_gap (int),
        attainment_pct (float), total_downtime_hours (float),
        availability_pct (float), plan_met (bool), status_message (str).
        Numeric values are not rounded.

    Raises:
        TypeError: If *records* is not a list or contains a non-record item.
        ValueError: If *records* is empty.
    """
    recs = _validate_record_list(records)

    record_count = len(recs)
    dates = [r.production_date for r in recs]
    total_planned = sum(r.planned_units for r in recs)
    total_actual = sum(r.actual_units for r in recs)
    total_downtime = float(sum(r.downtime_hours for r in recs))

    production_gap = calculate_production_gap(total_planned, total_actual)

    return {
        "record_count": record_count,
        "date_from": min(dates).isoformat(),
        "date_to": max(dates).isoformat(),
        "total_planned_units": total_planned,
        "total_actual_units": total_actual,
        "production_gap": production_gap,
        "attainment_pct": calculate_attainment_pct(total_planned, total_actual),
        "total_downtime_hours": total_downtime,
        "availability_pct": calculate_availability_pct(
            total_downtime, record_count * SHIFT_HOURS
        ),
        "plan_met": total_actual >= total_planned,
        "status_message": _build_status_message(production_gap),
    }


def summarize_by(records: list, group_field: str) -> dict:
    """Group records by a field and summarize each group.

    Args:
        records: Non-empty list of ProductionRecord objects.
        group_field: One of 'production_date', 'machine_id',
            'product_code', 'shift'.

    Returns:
        ``{group_value: summary dict}``. Group values are strings as in
        to_dict() (ISO date, shift value, machine_id, product_code).
        Keys are ordered: shifts in enum order (morning, afternoon,
        night), all other fields in ascending order.

    Raises:
        TypeError: If group_field is not a str, *records* is not a list,
            or contains a non-record item.
        ValueError: If group_field is not supported or *records* is empty.
    """
    if not isinstance(group_field, str):
        raise TypeError("Gruplama alanı (group_field) metin (str) olmalıdır.")
    if group_field not in GROUP_FIELDS:
        valid = ", ".join(GROUP_FIELDS)
        raise ValueError(
            f"Geçersiz gruplama alanı: '{group_field}'. Geçerli değerler: {valid}."
        )
    recs = _validate_record_list(records)

    groups: dict[str, list[ProductionRecord]] = {}
    for rec in recs:
        groups.setdefault(_group_value(rec, group_field), []).append(rec)

    ordered_keys = sorted(groups, key=lambda v: _group_sort_key(group_field, v))
    return {key: summarize_records(groups[key]) for key in ordered_keys}
