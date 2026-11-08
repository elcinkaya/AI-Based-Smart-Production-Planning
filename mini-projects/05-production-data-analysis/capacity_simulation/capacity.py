"""
capacity.py – Vectorized theoretical and effective capacity (NumPy).

Vectorized versions of the Mini Project 1 formulas (MP1 Section 2.2):
- theoretical_capacity = working_hours * 3600 / cycle_time_sec
- effective_capacity   = theoretical_capacity * efficiency_pct / 100

The capacity formulas live only in this module; other modules call these
functions instead of recomputing capacity.  Validation follows the MP1
rules.  No Python loops over machines or days, inputs are never modified.

Author: Kişi A
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import numpy as np


def _to_float_array(values: np.ndarray, field_name: str, ndim: int) -> np.ndarray:
    """Convert *values* to a float64 array and check dimensionality.

    The input is not modified; a converted view/copy is returned.

    Args:
        values: Numeric array (or array-like) to convert.
        field_name: Field name used in the error message.
        ndim: Required number of dimensions.

    Returns:
        float64 array with ``ndim`` dimensions.

    Raises:
        ValueError: If the array is not numeric (text, bool, object), has
            the wrong number of dimensions, is empty or contains NaN/inf.
    """
    array = np.asarray(values)
    if array.dtype.kind not in "iuf":
        raise ValueError(f"{field_name} yalnızca sayısal değerler içermelidir.")
    if array.ndim != ndim:
        raise ValueError(f"{field_name} {ndim} boyutlu bir dizi olmalıdır (verilen: {array.ndim}).")
    if array.size == 0:
        raise ValueError(f"{field_name} boş olamaz.")
    array = array.astype(np.float64, copy=False)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} NaN veya sonsuz değer içeremez.")
    return array


def calculate_theoretical_capacity_array(
    working_hours: np.ndarray,
    cycle_time_sec: np.ndarray,
) -> np.ndarray:
    """Calculate theoretical daily capacity for every machine.

    Vectorized MP1 ``theoretical_capacity``:
    ``working_hours * 3600 / cycle_time_sec``.

    Args:
        working_hours: float64 array of shape (M,), hours/day (0 < x <= 24).
        cycle_time_sec: float64 array of shape (M,), seconds/unit (x > 0).

    Returns:
        float64 array of shape (M,), units/day.

    Raises:
        ValueError: If a value is out of range, the arrays are not numeric,
            not one-dimensional or their shapes differ.
    """
    hours = _to_float_array(working_hours, "working_hours", ndim=1)
    cycles = _to_float_array(cycle_time_sec, "cycle_time_sec", ndim=1)
    if hours.shape != cycles.shape:
        raise ValueError(
            f"working_hours {hours.shape} ve cycle_time_sec {cycles.shape} "
            f"dizilerinin şekilleri aynı olmalıdır."
        )
    if np.any((hours <= 0) | (hours > 24)):
        raise ValueError("Günlük çalışma süresi 0 ile 24 saat arasında olmalıdır (0 hariç).")
    if np.any(cycles <= 0):
        raise ValueError("Çevrim süresi sıfırdan büyük olmalıdır.")

    return hours * 3600 / cycles


def calculate_effective_capacity_array(
    theoretical_capacity: np.ndarray,
    efficiency_pct: np.ndarray,
) -> np.ndarray:
    """Calculate effective daily capacity for every machine and day.

    Vectorized MP1 ``effective_capacity`` using broadcasting:
    ``theoretical_capacity[:, None] * efficiency_pct / 100``.

    Args:
        theoretical_capacity: float64 array of shape (M,), units/day (x >= 0).
        efficiency_pct: float64 array of shape (M, D), percent (0 < x <= 100).

    Returns:
        float64 array of shape (M, D), units/day.

    Raises:
        ValueError: If a value is out of range, the arrays are not numeric,
            have the wrong dimensions or the machine counts differ.
    """
    theoretical = _to_float_array(theoretical_capacity, "theoretical_capacity", ndim=1)
    efficiency = _to_float_array(efficiency_pct, "efficiency_pct", ndim=2)
    if efficiency.shape[0] != theoretical.shape[0]:
        raise ValueError(
            f"efficiency_pct satır sayısı ({efficiency.shape[0]}) theoretical_capacity "
            f"uzunluğuyla ({theoretical.shape[0]}) aynı olmalıdır."
        )
    if np.any(theoretical < 0):
        raise ValueError("Teorik kapasite negatif olamaz.")
    if np.any((efficiency <= 0) | (efficiency > 100)):
        raise ValueError("Verimlilik 0 ile 100 arasında olmalıdır (0 hariç).")

    return theoretical[:, None] * efficiency / 100
