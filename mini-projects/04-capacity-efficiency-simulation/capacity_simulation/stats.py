"""
stats.py - Descriptive statistics and KPI summaries of a simulation.

Implements Section 3.5 of the Mini Project 4 plan:
- calculate_statistics: mean, std (ddof=0, population), min and max of an
  array, either over all cells or per axis index.
- summarize_simulation: the summary dictionary passed to report.py.
- summarize_by_machine: the same summary dictionary for every machine.

Total KPIs are computed with the Mini Project 3 functions
(calculate_production_gap, calculate_attainment_pct,
calculate_availability_pct) and the status message uses the same Turkish
texts as MP3.  Aggregations are vectorized NumPy operations; numbers are
NOT rounded here (rounding happens only in report.py).  No print/input.

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import datetime

import numpy as np

from capacity_simulation.models import SimulationResult
from production_records.analysis import (
    _build_status_message,
    calculate_attainment_pct,
    calculate_availability_pct,
    calculate_production_gap,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Population standard deviation (Section 3.1). Pandas defaults to ddof=1.
STD_DDOF: int = 0

#: Keys of every statistics block, in contract order.
STATISTIC_KEYS: tuple[str, ...] = ("mean", "std", "min", "max")

#: SimulationResult arrays summarized in the ``statistics`` entry.
STATISTIC_FIELDS: tuple[str, ...] = ("efficiency_pct", "effective_capacity", "actual_units")

#: Keys of the summary dictionary (Section 3.5), in contract order.
SIMULATION_SUMMARY_KEYS: tuple[str, ...] = (
    "machine_count",
    "day_count",
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
    "statistics",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_result(result) -> SimulationResult:
    """Ensure *result* is a SimulationResult.

    Raises:
        TypeError: If *result* is not a SimulationResult.
    """
    if not isinstance(result, SimulationResult):
        raise TypeError("result bir SimulationResult nesnesi olmalıdır.")
    return result


def _date_range(start_date: str, days: int) -> tuple[str, str]:
    """Return ISO (date_from, date_to) for *days* days starting at *start_date*."""
    first = datetime.date.fromisoformat(start_date)
    last = first + datetime.timedelta(days=days - 1)
    return first.isoformat(), last.isoformat()


def _build_summary(
    machine_count: int,
    day_count: int,
    date_from: str,
    date_to: str,
    total_planned: int,
    total_actual: int,
    total_downtime: float,
    total_working_hours: float,
    statistics: dict,
) -> dict:
    """Assemble one Section 3.5 summary dictionary from aggregated totals.

    The KPI values come from the MP3 analysis functions.

    Args:
        machine_count: Number of machines covered by the summary.
        day_count: Number of simulated days.
        date_from: ISO date of the first day.
        date_to: ISO date of the last day.
        total_planned: Sum of planned_units (Python int).
        total_actual: Sum of actual_units (Python int).
        total_downtime: Sum of downtime_hours (Python float).
        total_working_hours: sum(working_hours) * days (Python float).
        statistics: ``{field: {'mean', 'std', 'min', 'max'}}``.

    Returns:
        The summary dictionary (numbers not rounded).
    """
    production_gap = calculate_production_gap(total_planned, total_actual)
    return {
        "machine_count": machine_count,
        "day_count": day_count,
        "date_from": date_from,
        "date_to": date_to,
        "total_planned_units": total_planned,
        "total_actual_units": total_actual,
        "production_gap": production_gap,
        "attainment_pct": calculate_attainment_pct(total_planned, total_actual),
        "total_downtime_hours": total_downtime,
        "availability_pct": calculate_availability_pct(
            total_downtime, shift_hours=total_working_hours
        ),
        "plan_met": total_actual >= total_planned,
        "status_message": _build_status_message(production_gap),
        "statistics": statistics,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_statistics(values: np.ndarray, axis: int | None = None) -> dict:
    """Calculate mean, population standard deviation (ddof=0), min and max.

    Args:
        values: Numeric array of any shape, e.g. float64 array of shape
            (M, D). The array is not modified.
        axis: None for statistics over all cells; otherwise the axis to
            reduce (axis=1 -> one value per machine for an (M, D) matrix,
            axis=0 -> one value per day).

    Returns:
        ``{'mean', 'std', 'min', 'max'}``. With ``axis=None`` every value is
        a Python float; otherwise every value is a list of floats (one per
        remaining axis index).

    Raises:
        TypeError: If *values* is not an np.ndarray or *axis* is not an int.
        ValueError: If the array is empty, not numeric, contains NaN/inf or
            *axis* is out of range.
    """
    if not isinstance(values, np.ndarray):
        raise TypeError("values bir NumPy dizisi (np.ndarray) olmalıdır.")
    if values.dtype.kind not in "iuf":
        raise ValueError("values yalnızca sayısal değerler içermelidir.")
    if values.size == 0:
        raise ValueError("İstatistik hesaplamak için dizi boş olamaz.")
    if not np.all(np.isfinite(values)):
        raise ValueError("values NaN veya sonsuz değer içeremez.")
    if axis is not None:
        if isinstance(axis, bool) or not isinstance(axis, (int, np.integer)):
            raise TypeError("axis None veya tam sayı (int) olmalıdır.")
        if not -values.ndim <= axis < values.ndim:
            raise ValueError(
                f"axis değeri {axis}, {values.ndim} boyutlu dizi için geçersiz."
            )

    data = values.astype(np.float64, copy=False)
    mean = np.mean(data, axis=axis)
    std = np.std(data, axis=axis, ddof=STD_DDOF)
    minimum = np.min(data, axis=axis)
    maximum = np.max(data, axis=axis)

    if axis is None:
        return {
            "mean": float(mean),
            "std": float(std),
            "min": float(minimum),
            "max": float(maximum),
        }
    return {
        "mean": mean.tolist(),
        "std": std.tolist(),
        "min": minimum.tolist(),
        "max": maximum.tolist(),
    }


def summarize_simulation(result: SimulationResult) -> dict:
    """Build the Section 3.5 summary dictionary of a whole simulation.

    Args:
        result: SimulationResult with arrays of shape (M,) and (M, D).

    Returns:
        Dictionary with keys machine_count (int), day_count (int),
        date_from (str), date_to (str), total_planned_units (int),
        total_actual_units (int), production_gap (int), attainment_pct
        (float), total_downtime_hours (float), availability_pct (float),
        plan_met (bool), status_message (str) and statistics (dict with
        efficiency_pct, effective_capacity and actual_units blocks over all
        machine-days). availability uses
        ``total working hours = sum(working_hours) * days``.

    Raises:
        TypeError: If *result* is not a SimulationResult.
    """
    res = _validate_result(result)
    config = res.config
    machine_count, day_count = res.get_shape()
    date_from, date_to = _date_range(config.start_date, day_count)

    working_hours = np.array(config.working_hours, dtype=np.float64)
    statistics = {
        field: calculate_statistics(getattr(res, field)) for field in STATISTIC_FIELDS
    }
    return _build_summary(
        machine_count=machine_count,
        day_count=day_count,
        date_from=date_from,
        date_to=date_to,
        total_planned=int(res.planned_units.sum()),
        total_actual=int(res.actual_units.sum()),
        total_downtime=float(res.downtime_hours.sum()),
        total_working_hours=float(working_hours.sum() * day_count),
        statistics=statistics,
    )


def summarize_by_machine(result: SimulationResult) -> dict:
    """Build one Section 3.5 summary dictionary per machine.

    Totals and statistics are computed once, vectorized along axis=1
    (one value per machine); the per-machine dictionaries are then only
    assembled from those arrays, in ``config.machine_ids`` order.

    Args:
        result: SimulationResult with arrays of shape (M,) and (M, D).

    Returns:
        ``{machine_id: summary dict}``; every summary has machine_count 1
        and its availability uses ``working_hours * days`` of that machine.

    Raises:
        TypeError: If *result* is not a SimulationResult.
    """
    res = _validate_result(result)
    config = res.config
    _, day_count = res.get_shape()
    date_from, date_to = _date_range(config.start_date, day_count)

    planned = res.planned_units.sum(axis=1).tolist()                 # (M,)
    actual = res.actual_units.sum(axis=1).tolist()                   # (M,)
    downtime = res.downtime_hours.sum(axis=1).tolist()               # (M,)
    working = (np.array(config.working_hours, dtype=np.float64) * day_count).tolist()
    per_axis = {
        field: calculate_statistics(getattr(res, field), axis=1) for field in STATISTIC_FIELDS
    }

    summaries = {}
    for index, machine_id in enumerate(config.machine_ids):
        statistics = {
            field: {key: per_axis[field][key][index] for key in STATISTIC_KEYS}
            for field in STATISTIC_FIELDS
        }
        summaries[machine_id] = _build_summary(
            machine_count=1,
            day_count=day_count,
            date_from=date_from,
            date_to=date_to,
            total_planned=int(planned[index]),
            total_actual=int(actual[index]),
            total_downtime=float(downtime[index]),
            total_working_hours=float(working[index]),
            statistics=statistics,
        )
    return summaries
