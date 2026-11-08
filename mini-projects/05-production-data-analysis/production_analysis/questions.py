"""
questions.py - Business questions answered from the analysis data (plan 7.5).

answer_business_questions(analysis_df) returns ``{'q1': ..., 'q7': ...}``;
every entry is ``{'question': <Turkish text>, 'answer': <dict>}``.  Nothing is
hard-coded: every answer is computed from analysis_df with the KPI tables of
kpi.py (group totals) and the weekly summary of features.py.

Questions (Section 7.5):
    q1  Machine with the lowest plan attainment (attainment_pct).
    q2  Shift with the lowest availability (availability_pct).
    q3  Product with the highest total downtime and product with the highest
        downtime per record (total_downtime_hours / record_count).
    q4  Share of records that missed the plan, and the machine where this
        share is the highest.
    q5  Complete week (is_complete_week) with the largest production
        shortfall (most negative production_gap).
    q6  Machine with the highest capacity_utilization_pct.
    q7  Mean record attainment_pct of records with and without downtime and
        the difference in percentage points.  This question compares the
        record distributions, so - as defined in the plan - it uses the mean
        of the record values; the total-based ratios are given as extra keys.

Ties are resolved by the first group in sorted order (idxmin / idxmax).
Values are not rounded.  No row loops, no print/input; Turkish errors.

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import pandas as pd

from production_analysis.features import build_weekly_summary
from production_analysis.kpi import (
    KPI_INPUT_COLUMNS,
    _require_analysis_frame,
    calculate_kpi_table,
)
from production_analysis.schema import DATE_COLUMN

#: Columns analysis_df must contain to answer every question.
QUESTION_INPUT_COLUMNS: list[str] = KPI_INPUT_COLUMNS + [
    DATE_COLUMN,
    "machine_id",
    "product_code",
    "shift",
    "plan_met",
    "has_downtime",
    "week_start",
]

#: Turkish question texts (Section 7.5).
QUESTIONS: dict[str, str] = {
    "q1": "Hangi makinenin plan gerçekleşme oranı en düşük?",
    "q2": "Hangi vardiyada kullanılabilirlik en düşük?",
    "q3": "Hangi ürünün toplam duruşu, hangisinin kayıt başına ortalama duruşu en yüksek?",
    "q4": "Planı karşılamayan kayıtların oranı ve en yüksek olduğu makine nedir?",
    "q5": "Tam haftalar içinde toplam üretim açığı en büyük hafta hangisi?",
    "q6": "Hangi makinede kapasite kullanım oranı en yüksek?",
    "q7": "Duruşlu ve duruşsuz kayıtlar arasında ortalama gerçekleşme oranı farkı nedir?",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _values(series: pd.Series) -> dict:
    """Return ``{str(group): float}`` for a per-group Series."""
    return {str(key): float(value) for key, value in series.items()}


def _iso(value) -> str | None:
    """Return a timestamp as ISO date text (None for a missing value)."""
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _q1(machine: pd.DataFrame) -> dict:
    values = machine["attainment_pct"]
    worst = values.idxmin()
    return {"machine_id": str(worst), "attainment_pct": float(values[worst]), "values": _values(values)}


def _q2(shift: pd.DataFrame) -> dict:
    values = shift["availability_pct"]
    worst = values.idxmin()
    return {"shift": str(worst), "availability_pct": float(values[worst]), "values": _values(values)}


def _q3(product: pd.DataFrame) -> dict:
    totals = product["total_downtime_hours"]
    per_record = product["total_downtime_hours"] / product["record_count"]
    top_total = totals.idxmax()
    top_mean = per_record.idxmax()
    return {
        "total_product_code": str(top_total),
        "total_downtime_hours": float(totals[top_total]),
        "mean_product_code": str(top_mean),
        "mean_downtime_hours": float(per_record[top_mean]),
        "total_values": _values(totals),
        "mean_values": _values(per_record),
    }


def _q4(analysis_df: pd.DataFrame) -> dict:
    missed = ~analysis_df["plan_met"].astype(bool)
    record_count = int(len(analysis_df))
    missed_count = int(missed.sum())
    by_machine = (
        analysis_df[["machine_id"]]
        .assign(_missed=missed.astype("int64"))
        .groupby("machine_id", sort=True)
        .agg(missed_count=("_missed", "sum"), record_count=("_missed", "size"))
    )
    machine_pct = by_machine["missed_count"] / by_machine["record_count"] * 100.0
    worst = machine_pct.idxmax()
    return {
        "missed_count": missed_count,
        "record_count": record_count,
        "missed_pct": missed_count / record_count * 100.0,
        "machine_id": str(worst),
        "machine_missed_pct": float(machine_pct[worst]),
        "machine_missed_count": int(by_machine.loc[worst, "missed_count"]),
        "machine_record_count": int(by_machine.loc[worst, "record_count"]),
        "values": _values(machine_pct),
        "count_values": {str(key): int(value) for key, value in by_machine["missed_count"].items()},
    }


def _q5(analysis_df: pd.DataFrame) -> dict:
    weekly = build_weekly_summary(analysis_df)
    complete = weekly[weekly["is_complete_week"]]
    answer = {
        "week_count": int(len(weekly)),
        "complete_week_count": int(len(complete)),
        "week_start": None,
        "production_gap": None,
        "attainment_pct": None,
    }
    if complete.empty:
        return answer
    worst = complete["production_gap"].idxmin()
    answer.update(
        week_start=_iso(worst),
        production_gap=int(complete.loc[worst, "production_gap"]),
        attainment_pct=float(complete.loc[worst, "attainment_pct"]),
    )
    return answer


def _q6(machine: pd.DataFrame) -> dict:
    values = machine["capacity_utilization_pct"]
    best = values.idxmax()
    return {
        "machine_id": str(best),
        "capacity_utilization_pct": float(values[best]),
        "values": _values(values),
    }


def _q7(analysis_df: pd.DataFrame) -> dict:
    frame = analysis_df[["attainment_pct", "planned_units", "actual_units"]].assign(
        _with_downtime=analysis_df["has_downtime"].astype(bool)
    )
    stats = frame.groupby("_with_downtime").agg(
        record_count=("attainment_pct", "size"),
        mean_attainment_pct=("attainment_pct", "mean"),
        total_planned_units=("planned_units", "sum"),
        total_actual_units=("actual_units", "sum"),
    )
    stats = stats.reindex([True, False])
    total_based = stats["total_actual_units"] / stats["total_planned_units"] * 100.0

    def _float(value):
        return None if pd.isna(value) else float(value)

    with_mean = _float(stats.loc[True, "mean_attainment_pct"])
    without_mean = _float(stats.loc[False, "mean_attainment_pct"])
    difference = None if with_mean is None or without_mean is None else without_mean - with_mean
    return {
        "with_downtime_count": int(stats["record_count"].fillna(0).loc[True]),
        "without_downtime_count": int(stats["record_count"].fillna(0).loc[False]),
        "with_downtime_mean_attainment_pct": with_mean,
        "without_downtime_mean_attainment_pct": without_mean,
        "difference_pct_points": difference,
        "with_downtime_total_attainment_pct": _float(total_based.loc[True]),
        "without_downtime_total_attainment_pct": _float(total_based.loc[False]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer_business_questions(analysis_df: pd.DataFrame) -> dict:
    """Answer the seven business questions of Section 7.5 from the data.

    Input ``analysis_df`` (add_derived_columns output) needs the KPI input
    columns plus production_date, machine_id, product_code, shift, plan_met,
    has_downtime and week_start.

    Answer dictionaries (numbers are plain Python values, not rounded;
    percentages 0-100, downtime in hours, dates ISO text):
        q1: machine_id, attainment_pct, values {machine: attainment_pct}
        q2: shift, availability_pct, values {shift: availability_pct}
        q3: total_product_code, total_downtime_hours, mean_product_code,
            mean_downtime_hours, total_values, mean_values
        q4: missed_count, record_count, missed_pct, machine_id,
            machine_missed_pct, machine_missed_count, machine_record_count,
            values {machine: missed_pct}, count_values {machine: missed_count}
        q5: week_count, complete_week_count, week_start, production_gap,
            attainment_pct (None values when there is no complete week)
        q6: machine_id, capacity_utilization_pct, values
        q7: with_downtime_count, without_downtime_count,
            with_downtime_mean_attainment_pct,
            without_downtime_mean_attainment_pct, difference_pct_points
            (without - with), with/without_downtime_total_attainment_pct

    Args:
        analysis_df: Analysis DataFrame.

    Returns:
        ``{'q1': {'question': str, 'answer': dict}, ..., 'q7': {...}}``.

    Raises:
        TypeError: If analysis_df is not a DataFrame or a date column is not
            datetime64.
        ValueError: If analysis_df is empty or a required column is missing.
    """
    _require_analysis_frame(analysis_df, QUESTION_INPUT_COLUMNS)

    machine = calculate_kpi_table(analysis_df, "machine_id")
    product = calculate_kpi_table(analysis_df, "product_code")
    shift = calculate_kpi_table(analysis_df, "shift")

    answers = {
        "q1": _q1(machine),
        "q2": _q2(shift),
        "q3": _q3(product),
        "q4": _q4(analysis_df),
        "q5": _q5(analysis_df),
        "q6": _q6(machine),
        "q7": _q7(analysis_df),
    }
    return {key: {"question": QUESTIONS[key], "answer": answers[key]} for key in QUESTIONS}


__all__ = [
    "QUESTION_INPUT_COLUMNS",
    "QUESTIONS",
    "answer_business_questions",
]
