# production_records package – public exports managed by Kişi C.
"""
production_records – Production record model, CSV/JSON storage and KPI analysis.

Exposes the record model (Kişi A), file storage and RecordStore (Kişi B),
and KPI analysis and report functions (Kişi C) of Mini Project 03.

Mini Project: 03 – Production Record System
"""
from __future__ import annotations

# Record model and synthetic data (Kişi A)
from production_records.record import SHIFT_HOURS, ProductionRecord, Shift
from production_records.generate_records import generate_records

# Storage and repository (Kişi B)
from production_records.storage import (
    CSV_COLUMNS,
    JSON_SCHEMA_VERSION,
    append_record_csv,
    append_record_json,
    convert_records_file,
    load_records_csv,
    load_records_json,
    save_records_csv,
    save_records_json,
)
from production_records.record_store import RecordStore

# KPI analysis and reports (Kişi C)
from production_records.analysis import (
    GROUP_FIELDS,
    SUMMARY_KEYS,
    calculate_attainment_pct,
    calculate_availability_pct,
    calculate_production_gap,
    summarize_by,
    summarize_records,
)
from production_records.report import (
    build_record_table,
    build_summary_report,
    print_record_table,
    print_summary_report,
)

__all__ = [
    # Record model
    "SHIFT_HOURS",
    "Shift",
    "ProductionRecord",
    "generate_records",
    # Storage
    "CSV_COLUMNS",
    "JSON_SCHEMA_VERSION",
    "load_records_json",
    "save_records_json",
    "append_record_json",
    "load_records_csv",
    "save_records_csv",
    "append_record_csv",
    "convert_records_file",
    "RecordStore",
    # Analysis
    "GROUP_FIELDS",
    "SUMMARY_KEYS",
    "calculate_production_gap",
    "calculate_attainment_pct",
    "calculate_availability_pct",
    "summarize_records",
    "summarize_by",
    # Report
    "build_summary_report",
    "print_summary_report",
    "build_record_table",
    "print_record_table",
]
