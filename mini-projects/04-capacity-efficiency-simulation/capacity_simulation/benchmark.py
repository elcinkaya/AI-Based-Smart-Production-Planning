"""
benchmark.py - Python loop vs. NumPy speed comparison of effective capacity.

compare_loop_and_numpy() runs the same effective capacity calculation
twice on the same synthetic input:
1. a Python loop over machines and days calling the Mini Project 1 scalar
   functions (factory_model.calculations.theoretical_capacity and
   effective_capacity);
2. the vectorized capacity.py functions (Kişi A).
Both durations are measured with ``time.perf_counter`` and the results are
compared with ``np.allclose``.  Python loops over machines/days are allowed
only here (Section 3.1).  print is allowed in this module (Section 3.6).

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import platform
import time

import numpy as np

from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from capacity_simulation.models import DEFAULT_SEED
from factory_model import calculations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MACHINE_COUNT: int = 1000
DEFAULT_BENCHMARK_DAYS: int = 365

#: Value ranges of the synthetic benchmark input (all inside MP1 rules).
WORKING_HOURS_RANGE: tuple[float, float] = (4.0, 24.0)
CYCLE_TIME_SEC_RANGE: tuple[float, float] = (10.0, 120.0)
EFFICIENCY_PCT_RANGE: tuple[float, float] = (50.0, 100.0)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_size(value, field_name: str) -> int:
    """Validate a positive integer size.

    Raises:
        TypeError: If *value* is not an int (bool rejected).
        ValueError: If *value* < 1.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} tam sayı (int) olmalıdır.")
    if value < 1:
        raise ValueError(f"{field_name} en az 1 olmalıdır.")
    return value


def _build_input(machine_count: int, days: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create reproducible benchmark input with ``np.random.default_rng``.

    Returns:
        working_hours: float64 (M,), cycle_time_sec: float64 (M,),
        efficiency_pct: float64 (M, D).
    """
    rng = np.random.default_rng(DEFAULT_SEED)
    working_hours = rng.uniform(*WORKING_HOURS_RANGE, size=machine_count)
    cycle_time_sec = rng.uniform(*CYCLE_TIME_SEC_RANGE, size=machine_count)
    efficiency_pct = rng.uniform(*EFFICIENCY_PCT_RANGE, size=(machine_count, days))
    return working_hours, cycle_time_sec, efficiency_pct


def _loop_effective_capacity(
    working_hours: list, cycle_time_sec: list, efficiency_pct: list
) -> list:
    """Reference implementation: MP1 scalar functions inside Python loops."""
    result = []
    for hours, cycle, row in zip(working_hours, cycle_time_sec, efficiency_pct):
        theoretical = calculations.theoretical_capacity(hours, cycle)
        result.append([calculations.effective_capacity(theoretical, eff) for eff in row])
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare_loop_and_numpy(
    machine_count: int = DEFAULT_MACHINE_COUNT, days: int = DEFAULT_BENCHMARK_DAYS
) -> dict:
    """Measure the Python loop and NumPy versions of effective capacity.

    Args:
        machine_count: Number of machines M (int >= 1).
        days: Number of days D (int >= 1).

    Returns:
        Dictionary with machine_count, days, cell_count (M * D),
        loop_seconds, numpy_seconds, speedup (loop / numpy),
        results_match (np.allclose of both (M, D) results),
        numpy_version and python_version. All durations are real
        ``time.perf_counter`` measurements.

    Raises:
        TypeError: If a size is not an int.
        ValueError: If a size is smaller than 1.
    """
    machines = _validate_size(machine_count, "machine_count")
    day_count = _validate_size(days, "days")
    working_hours, cycle_time_sec, efficiency_pct = _build_input(machines, day_count)

    # Plain Python lists for the loop version (conversion is not timed).
    hours_list = working_hours.tolist()
    cycle_list = cycle_time_sec.tolist()
    efficiency_list = efficiency_pct.tolist()

    start = time.perf_counter()
    loop_result = _loop_effective_capacity(hours_list, cycle_list, efficiency_list)
    loop_seconds = time.perf_counter() - start

    start = time.perf_counter()
    theoretical = calculate_theoretical_capacity_array(working_hours, cycle_time_sec)
    numpy_result = calculate_effective_capacity_array(theoretical, efficiency_pct)
    numpy_seconds = time.perf_counter() - start

    results_match = bool(np.allclose(np.array(loop_result), numpy_result))
    speedup = loop_seconds / numpy_seconds if numpy_seconds > 0 else float("inf")
    return {
        "machine_count": machines,
        "days": day_count,
        "cell_count": machines * day_count,
        "loop_seconds": loop_seconds,
        "numpy_seconds": numpy_seconds,
        "speedup": speedup,
        "results_match": results_match,
        "numpy_version": np.__version__,
        "python_version": platform.python_version(),
    }


def build_benchmark_report(benchmark: dict) -> str:
    """Build the Turkish benchmark report text from compare_loop_and_numpy().

    Raises:
        TypeError: If *benchmark* is not a dict.
    """
    if not isinstance(benchmark, dict):
        raise TypeError("Hız karşılaştırması sonucu bir sözlük (dict) olmalıdır.")
    sep = "=" * 46
    match = "Evet" if benchmark["results_match"] else "Hayır"
    lines = [
        sep,
        "  DÖNGÜ / NUMPY HIZ KARŞILAŞTIRMASI",
        sep,
        f"  {'Boyut':<22}: {benchmark['machine_count']} makine × {benchmark['days']} gün",
        f"  {'Hücre sayısı':<22}: {benchmark['cell_count']}",
        f"  {'Python döngüsü':<22}: {benchmark['loop_seconds']:.4f} sn",
        f"  {'NumPy (vektörel)':<22}: {benchmark['numpy_seconds']:.4f} sn",
        f"  {'Hızlanma':<22}: {benchmark['speedup']:.1f} kat",
        f"  {'Sonuçlar aynı mı':<22}: {match} (np.allclose)",
        f"  {'Ortam':<22}: Python {benchmark['python_version']}, "
        f"NumPy {benchmark['numpy_version']}",
        sep,
    ]
    return "\n".join(lines)


def print_benchmark_report(benchmark: dict) -> None:
    """Print the report built by build_benchmark_report()."""
    print(build_benchmark_report(benchmark))


if __name__ == "__main__":
    print_benchmark_report(compare_loop_and_numpy())
