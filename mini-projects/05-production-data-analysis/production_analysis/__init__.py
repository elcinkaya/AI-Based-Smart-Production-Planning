# production_analysis package - public exports managed by Kişi C.
"""
production_analysis - Pandas data preparation layer of Mini Project 05.

Data flow (plan Section 3.1):

    MP4 simulate + simulation_to_records -> MP3 RecordStore
      -> raw_records_clean.csv (600) -> inject_faults (seed 42)
      -> raw_records_dirty.csv / .json (610) -> load_records_dataframe
      -> clean_records (546) -> add_derived_columns
      -> KPI tables, daily / weekly series -> business questions
      -> analysis files (data/*.csv)

Modules and owners:
    schema, masters, loading, dataset, fault_injection  (Kişi A)
    cleaning, features                                  (Kişi B)
    kpi, questions, report                              (Kişi C)

Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

# Contract, masters, loading and raw data (Kişi A)
from production_analysis.schema import (
    CLEANING_LOG_COLUMNS,
    DATE_COLUMN,
    DERIVED_COLUMNS,
    FAULT_LOG_COLUMNS,
    ISSUE_ACTIONS,
    ISSUE_CODES,
    KEY_FIELDS,
    KPI_COLUMNS,
    MACHINE_MASTER_COLUMNS,
    PRODUCT_MASTER_COLUMNS,
    RECORD_COLUMNS,
    SHIFT_HOURS,
    VALID_SHIFTS,
)
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.loading import (
    dataframe_to_records,
    load_records_dataframe,
    records_to_dataframe,
)
from production_analysis.fault_injection import (
    DUPLICATE_COUNT,
    FAULT_PLAN,
    inject_faults,
    save_dirty_records,
)
from production_analysis.dataset import (
    DIRTY_CSV_FILENAME,
    DIRTY_JSON_FILENAME,
    FAULT_LOG_FILENAME,
    RAW_CLEAN_FILENAME,
    build_clean_records,
    write_raw_datasets,
)

# Cleaning and derived columns (Kişi B)
from production_analysis.cleaning import clean_records, summarize_cleaning
from production_analysis.features import (
    DAILY_SERIES_COLUMNS,
    WEEKLY_SUMMARY_COLUMNS,
    add_derived_columns,
    build_daily_series,
    build_weekly_summary,
)

# KPI, business questions and report (Kişi C)
from production_analysis.kpi import (
    KPI_TABLE_GROUPS,
    build_kpi_tables,
    calculate_group_date_ranges,
    calculate_kpi_table,
    kpi_table_to_group_summaries,
    summarize_kpi,
)
from production_analysis.questions import QUESTIONS, answer_business_questions
from production_analysis.report import (
    build_analysis_report,
    print_analysis_report,
    save_analysis_outputs,
)

__all__ = [
    # Contract (schema)
    "SHIFT_HOURS",
    "RECORD_COLUMNS",
    "VALID_SHIFTS",
    "KEY_FIELDS",
    "ISSUE_ACTIONS",
    "ISSUE_CODES",
    "DERIVED_COLUMNS",
    "KPI_COLUMNS",
    "DATE_COLUMN",
    "MACHINE_MASTER_COLUMNS",
    "PRODUCT_MASTER_COLUMNS",
    "CLEANING_LOG_COLUMNS",
    "FAULT_LOG_COLUMNS",
    # Masters and loading
    "build_machine_master",
    "build_product_master",
    "load_records_dataframe",
    "records_to_dataframe",
    "dataframe_to_records",
    # Raw data and fault injection
    "FAULT_PLAN",
    "DUPLICATE_COUNT",
    "inject_faults",
    "save_dirty_records",
    "RAW_CLEAN_FILENAME",
    "DIRTY_CSV_FILENAME",
    "DIRTY_JSON_FILENAME",
    "FAULT_LOG_FILENAME",
    "build_clean_records",
    "write_raw_datasets",
    # Cleaning and features
    "clean_records",
    "summarize_cleaning",
    "DAILY_SERIES_COLUMNS",
    "WEEKLY_SUMMARY_COLUMNS",
    "add_derived_columns",
    "build_daily_series",
    "build_weekly_summary",
    # KPI
    "KPI_TABLE_GROUPS",
    "calculate_kpi_table",
    "summarize_kpi",
    "kpi_table_to_group_summaries",
    "calculate_group_date_ranges",
    "build_kpi_tables",
    # Business questions
    "QUESTIONS",
    "answer_business_questions",
    # Report and export
    "build_analysis_report",
    "print_analysis_report",
    "save_analysis_outputs",
]
