"""
schema.py - Shared column contract, constants and issue codes of Mini Project 5.

This module is the single source of the DataFrame contract (plan Sections 3.2
and 3.3).  The other modules (cleaning, features, kpi, questions, report) import
their column lists and issue codes from here instead of repeating them.

Contents:
- RECORD_COLUMNS: raw/clean record columns; identical to MP3 ``CSV_COLUMNS``
  (same names, same order).
- VALID_SHIFTS: shift values taken from the MP3 ``Shift`` enum.
- KEY_FIELDS: fields whose absence makes a record unusable (missing_key_field).
- ISSUE_ACTIONS: cleaning issue code -> action (``'dropped'`` or ``'filled'``).
- DERIVED_COLUMNS: columns added to ``clean_df`` to obtain ``analysis_df``.
- KPI_COLUMNS: columns of every KPI table (row = group).

Additional helper lists (not named in the plan, derived only from Section 3.2
so that the contract is written in one place):
- INT_COLUMNS, FLOAT_COLUMNS, TEXT_COLUMNS, DATE_COLUMN: typed column groups of
  ``clean_df``.
- MACHINE_MASTER_COLUMNS, PRODUCT_MASTER_COLUMNS: master table columns.
- CLEANING_LOG_COLUMNS, FAULT_LOG_COLUMNS: log table columns.
- ISSUE_CODES: issue codes in the Section 3.3 table order.

Nothing in this module computes anything; it only defines constants.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

from production_records.record import SHIFT_HOURS, Shift
from production_records.storage import CSV_COLUMNS, JSON_SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Record columns (Section 3.2) - identical to MP3 CSV_COLUMNS
# ---------------------------------------------------------------------------

#: Raw and clean record columns, same names and order as MP3 ``CSV_COLUMNS``:
#: record_id, production_date, shift, machine_id, product_code,
#: planned_units, actual_units, downtime_hours.
RECORD_COLUMNS: list[str] = list(CSV_COLUMNS)

#: Valid shift values (MP3 ``Shift`` enum): morning, afternoon, night.
VALID_SHIFTS: list[str] = [shift.value for shift in Shift]

#: Fields whose absence is reported as ``missing_key_field`` (Section 3.3).
KEY_FIELDS: list[str] = [
    "production_date",
    "shift",
    "machine_id",
    "product_code",
    "planned_units",
]

# ---------------------------------------------------------------------------
# Cleaning issue codes (Section 3.3)
# ---------------------------------------------------------------------------

#: Cleaning issue code -> action written to the cleaning log.
#: Only ``missing_downtime_hours`` is repaired (filled with 0.0, MP3 default).
ISSUE_ACTIONS: dict[str, str] = {
    "missing_key_field": "dropped",
    "missing_actual_units": "dropped",
    "missing_downtime_hours": "filled",
    "invalid_date": "dropped",
    "invalid_shift": "dropped",
    "unknown_machine_id": "dropped",
    "unknown_product_code": "dropped",
    "invalid_planned_units": "dropped",
    "invalid_actual_units": "dropped",
    "invalid_downtime_hours": "dropped",
    "duplicate_key": "dropped",
}

#: Issue codes in the order of the Section 3.3 table.
ISSUE_CODES: list[str] = list(ISSUE_ACTIONS)

# ---------------------------------------------------------------------------
# Derived and KPI columns (Sections 3.2 and 3.4)
# ---------------------------------------------------------------------------

#: Columns added by ``add_derived_columns`` (analysis_df = clean_df + these).
DERIVED_COLUMNS: list[str] = [
    "line_id",
    "priority",
    "shift_effective_capacity",
    "production_gap",
    "attainment_pct",
    "availability_pct",
    "capacity_utilization_pct",
    "plan_met",
    "has_downtime",
    "weekday",
    "week_start",
]

#: Columns of every KPI table (one row per group).  The first seven names
#: except capacity_utilization_pct equal the MP3 summary dictionary keys.
KPI_COLUMNS: list[str] = [
    "record_count",
    "total_planned_units",
    "total_actual_units",
    "production_gap",
    "attainment_pct",
    "total_downtime_hours",
    "availability_pct",
    "capacity_utilization_pct",
    "downtime_event_count",
    "attainment_pct_std",
    "plan_met",
    "status_message",
]

# ---------------------------------------------------------------------------
# Typed column groups of clean_df (Section 3.2)
# ---------------------------------------------------------------------------

#: clean_df int64 columns.
INT_COLUMNS: list[str] = ["record_id", "planned_units", "actual_units"]

#: clean_df float64 columns.
FLOAT_COLUMNS: list[str] = ["downtime_hours"]

#: clean_df text columns.
TEXT_COLUMNS: list[str] = ["shift", "machine_id", "product_code"]

#: clean_df datetime64 column.
DATE_COLUMN: str = "production_date"

# ---------------------------------------------------------------------------
# Master and log tables (Sections 3.2, 3.3 and 5)
# ---------------------------------------------------------------------------

#: Columns of ``build_machine_master`` (one row per factory machine).
MACHINE_MASTER_COLUMNS: list[str] = [
    "machine_id",
    "name",
    "line_id",
    "working_hours",
    "cycle_time_sec",
    "efficiency_pct",
    "is_available",
    "shift_count",
    "theoretical_capacity",
    "effective_capacity",
    "shift_effective_capacity",
]

#: Columns of ``build_product_master`` (one row per factory product).
PRODUCT_MASTER_COLUMNS: list[str] = [
    "product_code",
    "name",
    "processing_time_sec",
    "priority",
]

#: Columns of ``cleaning_log_df``; action is ``ISSUE_ACTIONS[issue]``.
CLEANING_LOG_COLUMNS: list[str] = ["record_id", "issue", "action"]

#: Columns of the fault injection log (``inject_faults`` second result).
FAULT_LOG_COLUMNS: list[str] = ["record_id", "fault_type"]

__all__ = [
    "SHIFT_HOURS",
    "JSON_SCHEMA_VERSION",
    "RECORD_COLUMNS",
    "VALID_SHIFTS",
    "KEY_FIELDS",
    "ISSUE_ACTIONS",
    "ISSUE_CODES",
    "DERIVED_COLUMNS",
    "KPI_COLUMNS",
    "INT_COLUMNS",
    "FLOAT_COLUMNS",
    "TEXT_COLUMNS",
    "DATE_COLUMN",
    "MACHINE_MASTER_COLUMNS",
    "PRODUCT_MASTER_COLUMNS",
    "CLEANING_LOG_COLUMNS",
    "FAULT_LOG_COLUMNS",
]
