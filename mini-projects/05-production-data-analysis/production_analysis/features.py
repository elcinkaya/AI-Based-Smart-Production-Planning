"""
features.py - Derived columns and daily / weekly series (plan 3.2 and 3.5).

- add_derived_columns: clean_df + machine/product masters -> analysis_df
  (clean_df columns followed by DERIVED_COLUMNS).
- build_daily_series: complete daily series between the first and last
  production date (missing days included), with a 7-day moving average.
- build_weekly_summary: one row per week; weeks start on Monday.

Rules of this module:
- The masters are joined with ``merge(..., how='left',
  validate='many_to_one')``; an id without a master row raises ValueError.
- No capacity formula is repeated: capacity_utilization_pct uses the
  master's ``shift_effective_capacity`` (computed in masters.py with the
  MP1/MP4 functions).
- Shift length is SHIFT_HOURS (8 h, MP3); percentages are 0-100.
- Group totals use ``groupby(...).agg(...)`` with named aggregation.
- Values are not rounded (rounding happens only in the report).
- No row-by-row DataFrame iteration, no row-wise apply, no per-row loop.
- Input frames are never modified; new frames are returned.
- No print/input; error messages are Turkish.

Author: Kişi B
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import pandas as pd

from production_analysis.schema import (
    DATE_COLUMN,
    DERIVED_COLUMNS,
    RECORD_COLUMNS,
    SHIFT_HOURS,
)

#: Machine master columns used by add_derived_columns.
_MACHINE_COLUMNS: list[str] = ["machine_id", "line_id", "shift_effective_capacity"]

#: Product master columns used by add_derived_columns.
_PRODUCT_COLUMNS: list[str] = ["product_code", "priority"]

#: analysis_df columns needed by the daily / weekly series.
_SERIES_COLUMNS: list[str] = [DATE_COLUMN, "planned_units", "actual_units", "downtime_hours"]

#: Columns of build_daily_series (index: production_date).
DAILY_SERIES_COLUMNS: list[str] = [
    "record_count",
    "total_planned_units",
    "total_actual_units",
    "total_downtime_hours",
    "production_gap",
    "attainment_pct",
    "actual_units_ma7",
    "is_missing_day",
]

#: Columns of build_weekly_summary (index: week_start).
WEEKLY_SUMMARY_COLUMNS: list[str] = [
    "day_count",
    "record_count",
    "total_planned_units",
    "total_actual_units",
    "total_downtime_hours",
    "production_gap",
    "attainment_pct",
    "is_complete_week",
]

#: Moving average window of the daily series (days).
MOVING_AVERAGE_DAYS: int = 7

_TOTALS = {
    "record_count": ("actual_units", "size"),
    "total_planned_units": ("planned_units", "sum"),
    "total_actual_units": ("actual_units", "sum"),
    "total_downtime_hours": ("downtime_hours", "sum"),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_frame(df, name: str) -> None:
    """Raise TypeError if *df* is not a pandas DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} bir pandas DataFrame olmalıdır.")


def _require_columns(df: pd.DataFrame, columns: list, name: str) -> None:
    """Raise ValueError if a required column is missing from *df*."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{name} içinde gerekli sütun(lar) eksik: {', '.join(missing)}")


def _require_not_empty(df: pd.DataFrame, name: str) -> None:
    """Raise ValueError if *df* has no rows."""
    if df.empty:
        raise ValueError(f"{name} boş; en az bir kayıt gereklidir.")


def _require_datetime(series: pd.Series, name: str) -> None:
    """Raise TypeError if *series* is not a datetime64 column."""
    if not pd.api.types.is_datetime64_any_dtype(series):
        raise TypeError(
            f"{name} sütunu datetime64 türünde olmalıdır (clean_records çıktısı beklenir)."
        )


def _merge_master(
    left: pd.DataFrame, master: pd.DataFrame, key: str, master_name: str
) -> pd.DataFrame:
    """Left-join *master* on *key* (many_to_one); unmatched ids raise ValueError."""
    try:
        merged = left.merge(
            master, on=key, how="left", validate="many_to_one", indicator="_merge_status"
        )
    except pd.errors.MergeError as err:
        raise ValueError(
            f"{master_name} içinde '{key}' değerleri benzersiz değil; birleştirme yapılamadı."
        ) from err
    unmatched = merged["_merge_status"].eq("left_only")
    if unmatched.any():
        ids = ", ".join(sorted(merged.loc[unmatched, key].astype(str).unique()))
        raise ValueError(f"{master_name} içinde karşılığı olmayan {key} değer(ler)i: {ids}")
    return merged.drop(columns="_merge_status")


def _add_gap_and_attainment(frame: pd.DataFrame) -> pd.DataFrame:
    """Add production_gap and attainment_pct (NaN when nothing was planned)."""
    planned = frame["total_planned_units"]
    frame["production_gap"] = frame["total_actual_units"] - planned
    frame["attainment_pct"] = (
        frame["total_actual_units"] / planned.where(planned > 0) * 100.0
    ).astype("float64")
    return frame


def _check_series_input(analysis_df: pd.DataFrame, extra: list) -> None:
    """Common validation of the series builders."""
    _require_frame(analysis_df, "analysis_df")
    _require_columns(analysis_df, _SERIES_COLUMNS + extra, "analysis_df")
    _require_not_empty(analysis_df, "analysis_df")
    _require_datetime(analysis_df[DATE_COLUMN], DATE_COLUMN)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_derived_columns(
    clean_df: pd.DataFrame,
    machine_master: pd.DataFrame,
    product_master: pd.DataFrame,
) -> pd.DataFrame:
    """Return analysis_df = clean_df columns + DERIVED_COLUMNS (Section 3.2).

    Input ``clean_df``: ``clean_records`` output (RECORD_COLUMNS,
    production_date datetime64).  ``machine_master`` needs machine_id,
    line_id, shift_effective_capacity; ``product_master`` needs
    product_code, priority.

    Added columns and dtypes:
        line_id (string): from the machine master;
        priority (int64): from the product master;
        shift_effective_capacity (float64, units/shift): from the machine
            master (no capacity formula is repeated here);
        production_gap (int64): actual_units - planned_units;
        attainment_pct (float64): actual_units / planned_units * 100;
        availability_pct (float64): (8 - downtime_hours) / 8 * 100;
        capacity_utilization_pct (float64):
            actual_units / shift_effective_capacity * 100;
        plan_met (bool): actual_units >= planned_units;
        has_downtime (bool): downtime_hours > 0;
        weekday (int64): 0 = Monday ... 6 = Sunday;
        week_start (datetime64): Monday of the record's week.
    Row order and count equal clean_df; index 0..n-1.

    Args:
        clean_df: Clean record frame.
        machine_master: Machine master table.
        product_master: Product master table.

    Returns:
        New analysis DataFrame.

    Raises:
        TypeError: If an argument is not a DataFrame or production_date is
            not datetime64.
        ValueError: If clean_df is empty, a column is missing, a master key
            is not unique, or a machine_id / product_code has no master row.
    """
    _require_frame(clean_df, "clean_df")
    _require_frame(machine_master, "machine_master")
    _require_frame(product_master, "product_master")
    _require_columns(clean_df, RECORD_COLUMNS, "clean_df")
    _require_columns(machine_master, _MACHINE_COLUMNS, "machine_master")
    _require_columns(product_master, _PRODUCT_COLUMNS, "product_master")
    _require_not_empty(clean_df, "clean_df")
    _require_datetime(clean_df[DATE_COLUMN], DATE_COLUMN)

    base = clean_df[RECORD_COLUMNS].reset_index(drop=True)
    machines = machine_master[_MACHINE_COLUMNS].copy()
    machines["machine_id"] = machines["machine_id"].astype("string")
    products = product_master[_PRODUCT_COLUMNS].copy()
    products["product_code"] = products["product_code"].astype("string")
    base = base.assign(
        machine_id=base["machine_id"].astype("string"),
        product_code=base["product_code"].astype("string"),
    )

    merged = _merge_master(base, machines, "machine_id", "machine_master")
    merged = _merge_master(merged, products, "product_code", "product_master")

    planned = merged["planned_units"]
    actual = merged["actual_units"]
    downtime = merged["downtime_hours"]
    capacity = merged["shift_effective_capacity"].astype("float64")
    dates = merged[DATE_COLUMN].dt.normalize()
    weekday = merged[DATE_COLUMN].dt.dayofweek.astype("int64")

    analysis_df = merged[RECORD_COLUMNS].copy()
    analysis_df["line_id"] = merged["line_id"].astype("string")
    analysis_df["priority"] = merged["priority"].astype("int64")
    analysis_df["shift_effective_capacity"] = capacity
    analysis_df["production_gap"] = (actual - planned).astype("int64")
    analysis_df["attainment_pct"] = (actual / planned * 100.0).astype("float64")
    analysis_df["availability_pct"] = ((SHIFT_HOURS - downtime) / SHIFT_HOURS * 100.0).astype(
        "float64"
    )
    analysis_df["capacity_utilization_pct"] = (actual / capacity * 100.0).astype("float64")
    analysis_df["plan_met"] = (actual >= planned).astype(bool)
    analysis_df["has_downtime"] = (downtime > 0).astype(bool)
    analysis_df["weekday"] = weekday
    analysis_df["week_start"] = dates - pd.to_timedelta(weekday, unit="D")
    return analysis_df[RECORD_COLUMNS + DERIVED_COLUMNS].reset_index(drop=True)


def build_daily_series(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Build the complete daily series (Section 3.5).

    Index: production_date (datetime64), every day from the first to the
    last production date (``freq='D'``), including days without records.

    Columns and dtypes:
        record_count (int64), total_planned_units (int64),
        total_actual_units (int64), total_downtime_hours (float64),
        production_gap (int64): total_actual_units - total_planned_units,
        attainment_pct (float64): total_actual / total_planned * 100,
            NaN on days without records,
        actual_units_ma7 (float64):
            total_actual_units.rolling(7, min_periods=7).mean(),
        is_missing_day (bool): True when the day has no record.
    On a missing day counts and totals are 0.

    Args:
        analysis_df: Frame with production_date (datetime64),
            planned_units, actual_units, downtime_hours (e.g. analysis_df or
            clean_df).

    Returns:
        New daily series DataFrame.

    Raises:
        TypeError: If analysis_df is not a DataFrame or production_date is
            not datetime64.
        ValueError: If analysis_df is empty or a column is missing.
    """
    _check_series_input(analysis_df, [])

    frame = analysis_df[_SERIES_COLUMNS].assign(
        **{DATE_COLUMN: analysis_df[DATE_COLUMN].dt.normalize()}
    )
    daily = frame.groupby(DATE_COLUMN).agg(**_TOTALS)

    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name=DATE_COLUMN)
    daily = daily.reindex(full_range, fill_value=0)
    daily = daily.astype(
        {
            "record_count": "int64",
            "total_planned_units": "int64",
            "total_actual_units": "int64",
            "total_downtime_hours": "float64",
        }
    )
    daily = _add_gap_and_attainment(daily)
    daily["actual_units_ma7"] = (
        daily["total_actual_units"]
        .rolling(MOVING_AVERAGE_DAYS, min_periods=MOVING_AVERAGE_DAYS)
        .mean()
        .astype("float64")
    )
    daily["is_missing_day"] = daily["record_count"].eq(0).astype(bool)
    return daily[DAILY_SERIES_COLUMNS]


def build_weekly_summary(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Build the weekly summary (Section 3.5); weeks start on Monday.

    Index: week_start (datetime64, Monday), one row per week that has at
    least one record, ascending.

    Columns and dtypes:
        day_count (int64): distinct production dates with records,
        record_count (int64), total_planned_units (int64),
        total_actual_units (int64), total_downtime_hours (float64),
        production_gap (int64), attainment_pct (float64),
        is_complete_week (bool): day_count == 7.
    The first and the last week may be partial.

    Args:
        analysis_df: ``add_derived_columns`` output (needs week_start).

    Returns:
        New weekly summary DataFrame.

    Raises:
        TypeError: If analysis_df is not a DataFrame or a date column is not
            datetime64.
        ValueError: If analysis_df is empty or a column is missing.
    """
    _check_series_input(analysis_df, ["week_start"])
    _require_datetime(analysis_df["week_start"], "week_start")

    frame = analysis_df[_SERIES_COLUMNS + ["week_start"]].assign(
        **{DATE_COLUMN: analysis_df[DATE_COLUMN].dt.normalize()}
    )
    weekly = frame.groupby("week_start").agg(
        day_count=(DATE_COLUMN, "nunique"),
        **_TOTALS,
    )
    weekly = weekly.astype(
        {
            "day_count": "int64",
            "record_count": "int64",
            "total_planned_units": "int64",
            "total_actual_units": "int64",
            "total_downtime_hours": "float64",
        }
    )
    weekly = _add_gap_and_attainment(weekly)
    weekly["is_complete_week"] = weekly["day_count"].eq(7).astype(bool)
    return weekly[WEEKLY_SUMMARY_COLUMNS]


__all__ = [
    "DAILY_SERIES_COLUMNS",
    "WEEKLY_SUMMARY_COLUMNS",
    "MOVING_AVERAGE_DAYS",
    "add_derived_columns",
    "build_daily_series",
    "build_weekly_summary",
]
