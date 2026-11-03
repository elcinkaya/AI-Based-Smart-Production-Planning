"""
generation.py – Controlled random matrices and the simulate() pipeline.

Implements the random generation and simulation rules of Mini Project 4:
- Section 3.3: random draw order and shapes (reproducibility contract).
- Section 3.4: planned / actual production formulas with ``np.rint``.

Rules followed in this module:
- Randomness comes only from a ``np.random.Generator`` created with
  ``np.random.default_rng(seed)`` and passed as a parameter; no global
  ``np.random.*`` calls.
- Every random draw is a full (M, D) matrix; there are no Python loops over
  machines or days.
- Capacity is computed only through the capacity.py functions (Kişi A).
- Input arrays are never modified; functions return new arrays.
- No print/input; error messages are Turkish.

Author: Kişi B
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import numpy as np

from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from capacity_simulation.models import (
    DOWNTIME_HOURS_RANGE,
    DOWNTIME_PROBABILITY,
    DOWNTIME_STEP_HOURS,
    LOAD_FACTOR_RANGE,
    PERFORMANCE_FACTOR_RANGE,
    SimulationConfig,
    SimulationResult,
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_rng(rng) -> np.random.Generator:
    """Ensure *rng* is a ``np.random.Generator``.

    Raises:
        TypeError: If *rng* is not a Generator.
    """
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng bir np.random.Generator nesnesi olmalıdır.")
    return rng


def _validate_shape(shape) -> tuple:
    """Validate a (M, D) matrix shape with positive integer sizes.

    Raises:
        TypeError: If *shape* is not a tuple of two integers.
        ValueError: If a size is smaller than 1.
    """
    if (
        not isinstance(shape, tuple)
        or len(shape) != 2
        or any(isinstance(s, bool) or not isinstance(s, (int, np.integer)) for s in shape)
    ):
        raise TypeError("shape iki tam sayıdan oluşan bir demet (M, D) olmalıdır.")
    if shape[0] < 1 or shape[1] < 1:
        raise ValueError("shape boyutları en az 1 olmalıdır.")
    return (int(shape[0]), int(shape[1]))


def _to_numeric_array(values: np.ndarray, field_name: str, ndim: int) -> np.ndarray:
    """Return *values* as a float64 array with ``ndim`` dimensions.

    The input is not modified.

    Raises:
        ValueError: If the array is not numeric, has the wrong number of
            dimensions or contains NaN/inf.
    """
    array = np.asarray(values)
    if array.dtype.kind not in "iuf":
        raise ValueError(f"{field_name} yalnızca sayısal değerler içermelidir.")
    if array.ndim != ndim:
        raise ValueError(f"{field_name} {ndim} boyutlu bir dizi olmalıdır (verilen: {array.ndim}).")
    array = array.astype(np.float64, copy=False)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} NaN veya sonsuz değer içeremez.")
    return array


def _check_same_shape(reference: np.ndarray, other: np.ndarray, ref_name: str, other_name: str) -> None:
    """Raise ValueError if two matrices do not have the same shape."""
    if reference.shape != other.shape:
        raise ValueError(
            f"{ref_name} {reference.shape} ve {other_name} {other.shape} "
            f"dizilerinin şekilleri aynı olmalıdır."
        )


def _check_machine_count(matrix: np.ndarray, vector: np.ndarray, matrix_name: str, vector_name: str) -> None:
    """Raise ValueError if the (M,) vector does not match the matrix rows."""
    if vector.shape[0] != matrix.shape[0]:
        raise ValueError(
            f"{vector_name} uzunluğu ({vector.shape[0]}) {matrix_name} satır sayısıyla "
            f"({matrix.shape[0]}) aynı olmalıdır."
        )


# ---------------------------------------------------------------------------
# Random generation (Section 3.3)
# ---------------------------------------------------------------------------

def create_rng(seed: int) -> np.random.Generator:
    """Create the only random generator of a simulation.

    Args:
        seed: Non-negative integer seed.

    Returns:
        ``np.random.default_rng(seed)``.

    Raises:
        TypeError: If *seed* is not an integer.
        ValueError: If *seed* is negative.
    """
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed tam sayı (int) olmalıdır.")
    if seed < 0:
        raise ValueError("seed 0 veya daha büyük olmalıdır.")
    return np.random.default_rng(seed)


def generate_efficiency_matrix(
    rng: np.random.Generator,
    efficiency_min_pct: np.ndarray,
    efficiency_max_pct: np.ndarray,
    days: int,
) -> np.ndarray:
    """Generate daily efficiency values (draw 1 of Section 3.3).

    ``rng.uniform(low[:, None], high[:, None], size=(M, D))``; each machine
    uses its own [efficiency_min_pct, efficiency_max_pct] range.

    Args:
        rng: Random generator from ``create_rng``.
        efficiency_min_pct: float64 array of shape (M,), percent (x > 0).
        efficiency_max_pct: float64 array of shape (M,), percent (min <= x <= 100).
        days: Number of days D (x >= 1).

    Returns:
        efficiency_pct: float64 array of shape (M, D), percent.

    Raises:
        TypeError: If *rng* or *days* has the wrong type.
        ValueError: If the bounds are invalid or their shapes differ.
    """
    _validate_rng(rng)
    low = _to_numeric_array(efficiency_min_pct, "efficiency_min_pct", ndim=1)
    high = _to_numeric_array(efficiency_max_pct, "efficiency_max_pct", ndim=1)
    _check_same_shape(low, high, "efficiency_min_pct", "efficiency_max_pct")
    shape = _validate_shape((low.shape[0], days))
    if np.any(low <= 0):
        raise ValueError("efficiency_min_pct değerleri sıfırdan büyük olmalıdır.")
    if np.any(high > 100):
        raise ValueError("efficiency_max_pct değerleri 100'ü aşamaz.")
    if np.any(low > high):
        raise ValueError("efficiency_min_pct, efficiency_max_pct değerinden büyük olamaz.")

    return rng.uniform(low[:, None], high[:, None], size=shape)


def generate_load_factor_matrix(rng: np.random.Generator, shape: tuple) -> np.ndarray:
    """Generate load factors (draw 2 of Section 3.3).

    ``rng.uniform(0.80, 1.00, size=(M, D))`` using ``LOAD_FACTOR_RANGE``.

    Args:
        rng: Random generator from ``create_rng``.
        shape: Matrix shape (M, D).

    Returns:
        load_factor: float64 array of shape (M, D), ratio in [0.80, 1.00).
    """
    _validate_rng(rng)
    shape = _validate_shape(shape)
    low, high = LOAD_FACTOR_RANGE
    return rng.uniform(low, high, size=shape)


def generate_downtime_matrix(
    rng: np.random.Generator,
    shape: tuple,
    working_hours: np.ndarray,
) -> np.ndarray:
    """Generate daily downtime hours (draws 3 and 4 of Section 3.3).

    Draw 3: ``rng.random((M, D))``; downtime occurs where the value is
    below ``DOWNTIME_PROBABILITY`` (0.30).
    Draw 4: ``rng.uniform(0.25, 3.0, size=(M, D))``; the amount is rounded
    to quarter hours with ``np.rint(x / 0.25) * 0.25`` (= ``round(x * 4) / 4``).
    Both draws are always full matrices and are made in this order, even
    for cells without downtime.  The result is capped with
    ``working_hours[:, None]``.

    Args:
        rng: Random generator from ``create_rng``.
        shape: Matrix shape (M, D).
        working_hours: float64 array of shape (M,), hours/day (0 < x <= 24).

    Returns:
        downtime_hours: float64 array of shape (M, D), hours; every value is
        0 or a multiple of 0.25 and <= the machine's working_hours.

    Raises:
        ValueError: If working_hours is invalid or does not match shape[0].
    """
    _validate_rng(rng)
    shape = _validate_shape(shape)
    hours = _to_numeric_array(working_hours, "working_hours", ndim=1)
    if hours.shape[0] != shape[0]:
        raise ValueError(
            f"working_hours uzunluğu ({hours.shape[0]}) makine sayısıyla ({shape[0]}) aynı olmalıdır."
        )
    if np.any((hours <= 0) | (hours > 24)):
        raise ValueError("Günlük çalışma süresi 0 ile 24 saat arasında olmalıdır (0 hariç).")

    occurrence = rng.random(shape)                                   # draw 3
    low, high = DOWNTIME_HOURS_RANGE
    amount = rng.uniform(low, high, size=shape)                      # draw 4
    amount = np.rint(amount / DOWNTIME_STEP_HOURS) * DOWNTIME_STEP_HOURS
    downtime = np.where(occurrence < DOWNTIME_PROBABILITY, amount, 0.0)
    return np.minimum(downtime, hours[:, None])


def generate_performance_factor_matrix(rng: np.random.Generator, shape: tuple) -> np.ndarray:
    """Generate performance factors (draw 5 of Section 3.3).

    ``rng.uniform(0.90, 1.05, size=(M, D))`` using ``PERFORMANCE_FACTOR_RANGE``.

    Args:
        rng: Random generator from ``create_rng``.
        shape: Matrix shape (M, D).

    Returns:
        performance_factor: float64 array of shape (M, D), ratio in [0.90, 1.05).
    """
    _validate_rng(rng)
    shape = _validate_shape(shape)
    low, high = PERFORMANCE_FACTOR_RANGE
    return rng.uniform(low, high, size=shape)


# ---------------------------------------------------------------------------
# Deterministic production formulas (Section 3.4)
# ---------------------------------------------------------------------------

def calculate_planned_units(effective_capacity: np.ndarray, load_factor: np.ndarray) -> np.ndarray:
    """Calculate planned production: ``rint(effective_capacity * load_factor)``.

    Args:
        effective_capacity: float64 array of shape (M, D), units/day (x > 0).
        load_factor: float64 array of shape (M, D), ratio (x > 0).

    Returns:
        planned_units: int64 array of shape (M, D), units (x >= 1).

    Raises:
        ValueError: If the shapes differ, a value is invalid or any planned
            cell is below 1.
    """
    capacity = _to_numeric_array(effective_capacity, "effective_capacity", ndim=2)
    load = _to_numeric_array(load_factor, "load_factor", ndim=2)
    _check_same_shape(capacity, load, "effective_capacity", "load_factor")
    if np.any(capacity <= 0):
        raise ValueError("effective_capacity değerleri sıfırdan büyük olmalıdır.")
    if np.any(load <= 0):
        raise ValueError("load_factor değerleri sıfırdan büyük olmalıdır.")

    planned = np.rint(capacity * load).astype(np.int64)
    if np.any(planned < 1):
        raise ValueError(
            "planned_units değeri 1'in altına düştü; efektif kapasite çok düşük "
            "(ör. çevrim süresi çok büyük)."
        )
    return planned


def calculate_actual_units(
    planned_units: np.ndarray,
    performance_factor: np.ndarray,
    downtime_hours: np.ndarray,
    working_hours: np.ndarray,
) -> np.ndarray:
    """Calculate actual production.

    ``max(0, rint(planned_units * performance_factor
    * (1 - downtime_hours / working_hours[:, None])))``.

    Args:
        planned_units: int64 array of shape (M, D), units (x >= 1).
        performance_factor: float64 array of shape (M, D), ratio (x >= 0).
        downtime_hours: float64 array of shape (M, D), hours
            (0 <= x <= working_hours).
        working_hours: float64 array of shape (M,), hours/day (0 < x <= 24).

    Returns:
        actual_units: int64 array of shape (M, D), units (x >= 0).

    Raises:
        ValueError: If the shapes differ or a value is invalid.
    """
    planned = _to_numeric_array(planned_units, "planned_units", ndim=2)
    performance = _to_numeric_array(performance_factor, "performance_factor", ndim=2)
    downtime = _to_numeric_array(downtime_hours, "downtime_hours", ndim=2)
    hours = _to_numeric_array(working_hours, "working_hours", ndim=1)
    _check_same_shape(planned, performance, "planned_units", "performance_factor")
    _check_same_shape(planned, downtime, "planned_units", "downtime_hours")
    _check_machine_count(planned, hours, "planned_units", "working_hours")
    if np.any(planned < 0):
        raise ValueError("planned_units değerleri negatif olamaz.")
    if np.any(performance < 0):
        raise ValueError("performance_factor değerleri negatif olamaz.")
    if np.any((hours <= 0) | (hours > 24)):
        raise ValueError("Günlük çalışma süresi 0 ile 24 saat arasında olmalıdır (0 hariç).")
    if np.any((downtime < 0) | (downtime > hours[:, None])):
        raise ValueError(
            "downtime_hours değerleri 0 ile makinenin working_hours değeri arasında olmalıdır."
        )

    actual = np.rint(planned * performance * (1 - downtime / hours[:, None]))
    return np.maximum(0, actual).astype(np.int64)


# ---------------------------------------------------------------------------
# Simulation pipeline
# ---------------------------------------------------------------------------

def simulate(config: SimulationConfig) -> SimulationResult:
    """Run the full capacity and efficiency simulation.

    Order: efficiency -> effective capacity (capacity.py) -> load factor ->
    planned -> downtime -> performance factor -> actual.  One generator is
    created with ``np.random.default_rng(config.seed)`` and the random draws
    follow Section 3.3 exactly:

    1. efficiency_pct      ``rng.uniform(low[:, None], high[:, None], (M, D))``
    2. load_factor         ``rng.uniform(0.80, 1.00, (M, D))``
    3. downtime occurrence ``rng.random((M, D))``
    4. downtime amount     ``rng.uniform(0.25, 3.0, (M, D))``
    5. performance_factor  ``rng.uniform(0.90, 1.05, (M, D))``

    The function is pure: the same configuration always gives the same
    result and the configuration is not modified.

    Args:
        config: Validated SimulationConfig (M machines, D days).

    Returns:
        SimulationResult with arrays of shape (M,) and (M, D).

    Raises:
        TypeError: If *config* is not a SimulationConfig.
        ValueError: If any planned_units cell is below 1.
    """
    if not isinstance(config, SimulationConfig):
        raise TypeError("config bir SimulationConfig nesnesi olmalıdır.")

    working_hours = np.array(config.working_hours, dtype=np.float64)
    cycle_time_sec = np.array(config.cycle_time_sec, dtype=np.float64)
    efficiency_min = np.array(config.efficiency_min_pct, dtype=np.float64)
    efficiency_max = np.array(config.efficiency_max_pct, dtype=np.float64)
    shape = (config.get_machine_count(), config.days)

    rng = create_rng(config.seed)

    theoretical_capacity = calculate_theoretical_capacity_array(working_hours, cycle_time_sec)
    efficiency_pct = generate_efficiency_matrix(rng, efficiency_min, efficiency_max, config.days)
    effective_capacity = calculate_effective_capacity_array(theoretical_capacity, efficiency_pct)
    load_factor = generate_load_factor_matrix(rng, shape)
    planned_units = calculate_planned_units(effective_capacity, load_factor)
    downtime_hours = generate_downtime_matrix(rng, shape, working_hours)
    performance_factor = generate_performance_factor_matrix(rng, shape)
    actual_units = calculate_actual_units(planned_units, performance_factor, downtime_hours, working_hours)

    return SimulationResult(
        config=config,
        theoretical_capacity=theoretical_capacity,
        efficiency_pct=efficiency_pct,
        effective_capacity=effective_capacity,
        planned_units=planned_units,
        downtime_hours=downtime_hours,
        actual_units=actual_units,
    )
