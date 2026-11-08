"""
kpi.py - Group aggregation and KPI tables (plan Sections 3.2 and 3.4).

- calculate_kpi_table: analysis_df -> one KPI row per group (KPI_COLUMNS).
- summarize_kpi: overall summary dictionary (MP3 summary keys + extras).
- kpi_table_to_group_summaries: KPI table -> ``{group: MP3 summary dict}``
  so the MP3 ``build_summary_report`` can print the groups.
- build_kpi_tables: the five standard tables (machine, product, shift, day,
  week) used by the report, the CSV export and the menu.
- calculate_group_date_ranges: first / last production date of each group
  (helper for kpi_table_to_group_summaries).

KPI rules (Section 3.4) - every KPI is computed from group *totals*, never as
the mean of record percentages:

    production_gap           = total_actual_units - total_planned_units
    attainment_pct           = total_actual_units / total_planned_units * 100
    availability_pct         = (record_count * 8 - total_downtime_hours)
                               / (record_count * 8) * 100
    capacity_utilization_pct = total_actual_units
                               / sum(shift_effective_capacity) * 100
    downtime_event_count     = number of records with downtime_hours > 0
    attainment_pct_std       = std of record attainment_pct (ddof=0)
    plan_met                 = total_actual_units >= total_planned_units
    status_message           = MP3 Turkish status texts

Rules of this module:
- Aggregation with ``groupby(...).agg(...)`` (named aggregation) and
  vectorized column arithmetic; no row loop, no iterrows / itertuples, no
  row-wise apply.
- Every standard deviation is called with ``ddof=0`` explicitly (MP4 rule).
- Values are never rounded (rounding happens only in report.py).
- Input frames are never modified.
- No print/input; error messages are Turkish.

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from production_analysis.schema import DATE_COLUMN, KPI_COLUMNS, SHIFT_HOURS
from production_records.analysis import SUMMARY_KEYS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: analysis_df columns needed to compute a KPI table.
KPI_INPUT_COLUMNS: list[str] = [
    "planned_units",
    "actual_units",
    "downtime_hours",
    "shift_effective_capacity",
    "attainment_pct",
]

#: Index label of the single row produced by ``group_by=None``.
ALL_GROUP_LABEL: str = "all"

#: Keys of ``build_kpi_tables`` -> grouping column (Section 5, Kişi C rules).
KPI_TABLE_GROUPS: dict[str, str] = {
    "machine": "machine_id",
    "product": "product_code",
    "shift": "shift",
    "day": DATE_COLUMN,
    "week": "week_start",
}

#: Extra keys of summarize_kpi in addition to the MP3 SUMMARY_KEYS.
EXTRA_SUMMARY_KEYS: tuple[str, ...] = (
    "capacity_utilization_pct",
    "downtime_event_count",
    "attainment_pct_std",
)

#: KPI columns copied into an MP3 summary dictionary (MP3 key names).
_MP3_KPI_KEYS: tuple[str, ...] = tuple(
    key for key in SUMMARY_KEYS if key not in ("date_from", "date_to")
)

_INT_KPI_COLUMNS: tuple[str, ...] = (
    "record_count",
    "total_planned_units",
    "total_actual_units",
    "production_gap",
    "downtime_event_count",
)
_FLOAT_KPI_COLUMNS: tuple[str, ...] = (
    "attainment_pct",
    "total_downtime_hours",
    "availability_pct",
    "capacity_utilization_pct",
    "attainment_pct_std",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_analysis_frame(analysis_df, columns: list) -> None:
    """Validate type, emptiness and required columns of *analysis_df*.

    Raises:
        TypeError: If analysis_df is not a DataFrame.
        ValueError: If analysis_df is empty or a required column is missing.
    """
    if not isinstance(analysis_df, pd.DataFrame):
        raise TypeError("analysis_df bir pandas DataFrame olmalıdır.")
    missing = [column for column in columns if column not in analysis_df.columns]
    if missing:
        raise ValueError(f"analysis_df içinde gerekli sütun(lar) eksik: {', '.join(missing)}")
    if analysis_df.empty:
        raise ValueError("KPI hesaplamak için analysis_df boş olamaz; en az bir kayıt gereklidir.")


def _normalize_group_by(group_by, analysis_df: pd.DataFrame) -> list[str] | None:
    """Return group_by as a list of column names (or None for one 'all' row).

    Raises:
        TypeError: If group_by is not None, a str or a list/tuple of str.
        ValueError: If the list is empty, repeats a name or names an unknown
            column.
    """
    if group_by is None:
        return None
    if isinstance(group_by, str):
        columns = [group_by]
    elif isinstance(group_by, (list, tuple)):
        if not all(isinstance(name, str) for name in group_by):
            raise TypeError("group_by listesindeki her eleman sütun adı (str) olmalıdır.")
        columns = list(group_by)
        if not columns:
            raise ValueError("group_by listesi boş olamaz.")
        if len(set(columns)) != len(columns):
            raise ValueError("group_by listesinde aynı sütun birden fazla kez yazılamaz.")
    else:
        raise TypeError(
            "group_by None, sütun adı (str) veya sütun adlarından oluşan liste olmalıdır; "
            f"verilen tür: {type(group_by).__name__}."
        )
    unknown = [name for name in columns if name not in analysis_df.columns]
    if unknown:
        raise ValueError(f"group_by için bilinmeyen sütun(lar): {', '.join(unknown)}")
    return columns


def build_status_messages(production_gap: pd.Series) -> pd.Series:
    """Return the MP3 status message for every production gap (vectorized).

    The texts are identical to MP3 ``summarize_records``:
    ``'Plan karşılandı. Fazla üretim: N adet.'`` (gap > 0),
    ``'Plan tam olarak gerçekleşti.'`` (gap == 0) and
    ``'Plan karşılanmadı. Üretim açığı: N adet.'`` (gap < 0).

    Args:
        production_gap: Integer Series of total_actual - total_planned.

    Returns:
        String Series with the same index.
    """
    gap = production_gap.astype("int64")
    surplus = "Plan karşılandı. Fazla üretim: " + gap.astype(str) + " adet."
    shortfall = "Plan karşılanmadı. Üretim açığı: " + gap.abs().astype(str) + " adet."
    messages = np.where(
        gap.gt(0).to_numpy(),
        surplus.to_numpy(dtype=object),
        np.where(gap.eq(0).to_numpy(), "Plan tam olarak gerçekleşti.", shortfall.to_numpy(dtype=object)),
    )
    return pd.Series(messages, index=production_gap.index, dtype="string")


def _group_key_to_text(value):
    """Return a group key as MP3-style text (ISO date for timestamps)."""
    if isinstance(value, tuple):
        return tuple(_group_key_to_text(item) for item in value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)


def _to_python(value):
    """Convert a NumPy / pandas scalar to the plain Python type."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_kpi_table(analysis_df: pd.DataFrame, group_by=None) -> pd.DataFrame:
    """Aggregate analysis_df into a KPI table (one row per group).

    Input ``analysis_df`` (``add_derived_columns`` output) needs:
        planned_units (int64), actual_units (int64), downtime_hours
        (float64), shift_effective_capacity (float64), attainment_pct
        (float64) and the grouping column(s).

    Output columns (exactly KPI_COLUMNS, in this order):
        record_count (int64), total_planned_units (int64),
        total_actual_units (int64), production_gap (int64),
        attainment_pct (float64, %), total_downtime_hours (float64, hours),
        availability_pct (float64, %), capacity_utilization_pct (float64, %),
        downtime_event_count (int64), attainment_pct_std (float64, ddof=0),
        plan_met (bool), status_message (string).
    Index: the group values (sorted ascending); a MultiIndex for a list of
    columns; a single row labelled ``'all'`` when ``group_by`` is None.
    Values are not rounded.

    Args:
        analysis_df: Analysis DataFrame.
        group_by: None, a column name or a list of column names.

    Returns:
        New KPI DataFrame.

    Raises:
        TypeError: If analysis_df is not a DataFrame or group_by has an
            unsupported type.
        ValueError: If analysis_df is empty, a required column is missing or
            group_by names an unknown column.
    """
    _require_analysis_frame(analysis_df, KPI_INPUT_COLUMNS)
    group_columns = _normalize_group_by(group_by, analysis_df)

    extra_columns = [
        column for column in (group_columns or []) if column not in KPI_INPUT_COLUMNS
    ]
    frame = analysis_df[KPI_INPUT_COLUMNS + extra_columns].assign(
        _downtime_event=analysis_df["downtime_hours"].gt(0).astype("int64")
    )
    if group_columns is None:
        keys = pd.Series(ALL_GROUP_LABEL, index=analysis_df.index)
    else:
        keys = group_columns[0] if len(group_columns) == 1 else group_columns

    grouped = frame.groupby(keys, sort=True, dropna=False)
    table = grouped.agg(
        record_count=("actual_units", "size"),
        total_planned_units=("planned_units", "sum"),
        total_actual_units=("actual_units", "sum"),
        total_downtime_hours=("downtime_hours", "sum"),
        total_shift_capacity=("shift_effective_capacity", "sum"),
        downtime_event_count=("_downtime_event", "sum"),
    )
    attainment_std = grouped["attainment_pct"].std(ddof=0)
    if group_columns is None:
        table.index.name = None

    scheduled_hours = table["record_count"] * SHIFT_HOURS
    table["production_gap"] = table["total_actual_units"] - table["total_planned_units"]
    table["attainment_pct"] = table["total_actual_units"] / table["total_planned_units"] * 100.0
    table["availability_pct"] = (
        (scheduled_hours - table["total_downtime_hours"]) / scheduled_hours * 100.0
    )
    table["capacity_utilization_pct"] = (
        table["total_actual_units"] / table["total_shift_capacity"] * 100.0
    )
    table["attainment_pct_std"] = attainment_std
    table["plan_met"] = table["total_actual_units"].ge(table["total_planned_units"])
    table["status_message"] = build_status_messages(table["production_gap"])

    table = table[KPI_COLUMNS].astype(
        {
            **{column: "int64" for column in _INT_KPI_COLUMNS},
            **{column: "float64" for column in _FLOAT_KPI_COLUMNS},
            "plan_met": bool,
        }
    )
    return table


def summarize_kpi(analysis_df: pd.DataFrame) -> dict:
    """Return the overall summary dictionary (Section 3.4).

    Keys: the MP3 summary keys (record_count, date_from, date_to,
    total_planned_units, total_actual_units, production_gap, attainment_pct,
    total_downtime_hours, availability_pct, plan_met, status_message) in MP3
    order, followed by capacity_utilization_pct, downtime_event_count and
    attainment_pct_std.  Dates are ISO text; numbers are plain Python values
    (not rounded).  The dictionary can be passed to MP3
    ``build_summary_report``.

    Args:
        analysis_df: Analysis DataFrame (needs production_date datetime64
            and the KPI input columns).

    Returns:
        Summary dictionary.

    Raises:
        TypeError: If analysis_df is not a DataFrame or production_date is
            not datetime64.
        ValueError: If analysis_df is empty or a column is missing.
    """
    _require_analysis_frame(analysis_df, KPI_INPUT_COLUMNS + [DATE_COLUMN])
    dates = analysis_df[DATE_COLUMN]
    if not pd.api.types.is_datetime64_any_dtype(dates):
        raise TypeError(f"{DATE_COLUMN} sütunu datetime64 türünde olmalıdır.")

    row = calculate_kpi_table(analysis_df).iloc[0]
    summary = {
        "record_count": int(row["record_count"]),
        "date_from": dates.min().date().isoformat(),
        "date_to": dates.max().date().isoformat(),
    }
    for key in _MP3_KPI_KEYS:
        if key not in summary:
            summary[key] = _to_python(row[key])
    summary["status_message"] = str(row["status_message"])
    for key in EXTRA_SUMMARY_KEYS:
        summary[key] = _to_python(row[key])
    return summary


def calculate_group_date_ranges(analysis_df: pd.DataFrame, group_by) -> dict:
    """Return ``{group_value: (date_from, date_to)}`` with ISO date texts.

    Group values are converted like in kpi_table_to_group_summaries (ISO
    text for dates, str otherwise; tuples for several columns).

    Args:
        analysis_df: Analysis DataFrame with production_date (datetime64).
        group_by: A column name or a list of column names.

    Returns:
        Dictionary of first / last production date per group.

    Raises:
        TypeError / ValueError: Same rules as calculate_kpi_table.
    """
    _require_analysis_frame(analysis_df, [DATE_COLUMN])
    group_columns = _normalize_group_by(group_by, analysis_df)
    if group_columns is None:
        raise ValueError("calculate_group_date_ranges için group_by belirtilmelidir.")
    keys = group_columns[0] if len(group_columns) == 1 else group_columns
    ranges = analysis_df.groupby(keys, sort=True).agg(
        date_from=(DATE_COLUMN, "min"), date_to=(DATE_COLUMN, "max")
    )
    date_from = ranges["date_from"].dt.strftime("%Y-%m-%d").tolist()
    date_to = ranges["date_to"].dt.strftime("%Y-%m-%d").tolist()
    labels = [_group_key_to_text(key) for key in ranges.index.tolist()]
    return dict(zip(labels, zip(date_from, date_to)))


def kpi_table_to_group_summaries(kpi_table: pd.DataFrame, date_ranges=None) -> dict:
    """Convert a KPI table into ``{group_value: summary dict}`` (MP3 format).

    Each summary dictionary has the MP3 summary keys (record_count,
    date_from, date_to, total_planned_units, total_actual_units,
    production_gap, attainment_pct, total_downtime_hours, availability_pct,
    plan_met, status_message) followed by EXTRA_SUMMARY_KEYS, so the result
    can be passed to MP3 ``build_summary_report`` as ``group_summaries``.
    Group values become MP3-style text: ISO dates for date indexes, str for
    other values (tuples for a MultiIndex).

    date_from / date_to: taken from *date_ranges* when given
    (``{group_value: (date_from, date_to)}``, e.g. from
    calculate_group_date_ranges); for a date index (day table) both equal the
    group date; otherwise None.

    Args:
        kpi_table: calculate_kpi_table output.
        date_ranges: Optional dictionary of ISO date ranges per group.

    Returns:
        Ordered dictionary in the KPI table row order.

    Raises:
        TypeError: If kpi_table is not a DataFrame or date_ranges is not a
            dict.
        ValueError: If a KPI column is missing.
    """
    if not isinstance(kpi_table, pd.DataFrame):
        raise TypeError("kpi_table bir pandas DataFrame olmalıdır.")
    if date_ranges is not None and not isinstance(date_ranges, dict):
        raise TypeError("date_ranges bir sözlük (dict) olmalıdır.")
    missing = [column for column in KPI_COLUMNS if column not in kpi_table.columns]
    if missing:
        raise ValueError(f"kpi_table içinde gerekli sütun(lar) eksik: {', '.join(missing)}")

    is_date_index = pd.api.types.is_datetime64_any_dtype(kpi_table.index)
    labels = [_group_key_to_text(key) for key in kpi_table.index.tolist()]
    # Column-wise conversion to plain Python lists (no row iteration).
    columns = {column: kpi_table[column].tolist() for column in KPI_COLUMNS}

    summaries: dict = {}
    for position, label in enumerate(labels):  # one entry per group, not per record
        if date_ranges is not None and label in date_ranges:
            date_from, date_to = date_ranges[label]
        elif is_date_index:
            date_from = date_to = label
        else:
            date_from = date_to = None
        summary = {
            "record_count": int(columns["record_count"][position]),
            "date_from": date_from,
            "date_to": date_to,
        }
        for key in _MP3_KPI_KEYS:
            if key not in summary:
                summary[key] = _to_python(columns[key][position])
        summary["status_message"] = str(columns["status_message"][position])
        for key in EXTRA_SUMMARY_KEYS:
            summary[key] = _to_python(columns[key][position])
        summaries[label] = summary
    return summaries


def build_kpi_tables(analysis_df: pd.DataFrame) -> dict:
    """Return the five standard KPI tables.

    Keys and grouping columns: machine (machine_id), product (product_code),
    shift (shift), day (production_date), week (week_start).  Every value is
    a calculate_kpi_table result.

    Args:
        analysis_df: Analysis DataFrame (add_derived_columns output).

    Returns:
        ``{'machine': df, 'product': df, 'shift': df, 'day': df, 'week': df}``.

    Raises:
        TypeError / ValueError: Same rules as calculate_kpi_table.
    """
    return {
        key: calculate_kpi_table(analysis_df, column) for key, column in KPI_TABLE_GROUPS.items()
    }


__all__ = [
    "KPI_INPUT_COLUMNS",
    "ALL_GROUP_LABEL",
    "KPI_TABLE_GROUPS",
    "EXTRA_SUMMARY_KEYS",
    "build_status_messages",
    "calculate_kpi_table",
    "summarize_kpi",
    "calculate_group_date_ranges",
    "kpi_table_to_group_summaries",
    "build_kpi_tables",
]
