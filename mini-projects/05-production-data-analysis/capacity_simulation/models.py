"""
models.py – Shared constants, SimulationConfig and SimulationResult.

This module is the common contract of Mini Project 4 (Section 3.2):
- Constants used by every module (same numbers as MP3 generate_records).
- SimulationConfig: validated simulation input (one entry per machine).
- SimulationResult: validated simulation output (NumPy arrays).

Validation reuses ``validate_number`` and ``validate_non_empty_str`` from
Mini Project 2 (factory_model/base.py).  No print/input is used here.

Author: Kişi A
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import datetime

import numpy as np

from factory_model.base import validate_non_empty_str, validate_number

# ---------------------------------------------------------------------------
# Constants (Section 3.2) – defined only here
# ---------------------------------------------------------------------------

DEFAULT_DAYS = 30
DEFAULT_SEED = 42
DEFAULT_START_DATE = '2026-10-01'
EFFICIENCY_DOWN_PCT = 10.0      # default min = base - 10
EFFICIENCY_UP_PCT = 5.0         # default max = min(100, base + 5)
LOAD_FACTOR_RANGE = (0.80, 1.00)
PERFORMANCE_FACTOR_RANGE = (0.90, 1.05)
DOWNTIME_PROBABILITY = 0.30
DOWNTIME_HOURS_RANGE = (0.25, 3.0)
DOWNTIME_STEP_HOURS = 0.25

# Internal validation limits (Section 3.2)
_MIN_DAYS = 1
_MAX_DAYS = 3650

_LIST_FIELDS = (
    "working_hours",
    "cycle_time_sec",
    "base_efficiency_pct",
    "efficiency_min_pct",
    "efficiency_max_pct",
)
_CONFIG_FIELDS = ("machine_ids",) + _LIST_FIELDS + ("days", "start_date", "seed")

_FLOAT_ARRAY_FIELDS = (
    "theoretical_capacity",
    "efficiency_pct",
    "effective_capacity",
    "downtime_hours",
)
_INT_ARRAY_FIELDS = ("planned_units", "actual_units")
_RESULT_ARRAY_FIELDS = (
    "theoretical_capacity",
    "efficiency_pct",
    "effective_capacity",
    "planned_units",
    "downtime_hours",
    "actual_units",
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_int(value, field_name: str, lower: int, upper: int | None = None) -> int:
    """Validate that *value* is an ``int`` (not ``bool``) within bounds.

    Args:
        value: The value to validate.
        field_name: Field name used in the error message.
        lower: Inclusive lower bound.
        upper: Inclusive upper bound or None.

    Returns:
        The validated integer.

    Raises:
        TypeError: If *value* is not an integer.
        ValueError: If *value* is outside the bounds.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} tam sayı (int) olmalıdır.")
    if value < lower or (upper is not None and value > upper):
        if upper is None:
            raise ValueError(f"{field_name} {lower} veya daha büyük olmalıdır.")
        raise ValueError(f"{field_name} {lower} ile {upper} arasında olmalıdır.")
    return value


def _validate_iso_date(value, field_name: str) -> str:
    """Validate an ISO ``YYYY-MM-DD`` date string.

    Args:
        value: The value to validate.
        field_name: Field name used in the error message.

    Returns:
        The normalized ISO date string.

    Raises:
        TypeError: If *value* is not a string.
        ValueError: If *value* is empty or not a valid ``YYYY-MM-DD`` date.
    """
    text = validate_non_empty_str(value, field_name)
    try:
        parsed = datetime.date.fromisoformat(text)
    except ValueError as err:
        raise ValueError(
            f"Geçersiz {field_name}: '{text}'. 'YYYY-MM-DD' biçiminde geçerli bir tarih olmalıdır."
        ) from err
    # fromisoformat also accepts e.g. '20261001'; only YYYY-MM-DD is allowed.
    if parsed.isoformat() != text:
        raise ValueError(
            f"Geçersiz {field_name}: '{text}'. 'YYYY-MM-DD' biçiminde geçerli bir tarih olmalıdır."
        )
    return text


def _validate_list(values, field_name: str) -> list:
    """Validate that *values* is a ``list``.

    Raises:
        TypeError: If *values* is not a list.
    """
    if not isinstance(values, list):
        raise TypeError(f"{field_name} bir liste (list) olmalıdır.")
    return values


# ---------------------------------------------------------------------------
# SimulationConfig
# ---------------------------------------------------------------------------

class SimulationConfig:
    """Validated input of a capacity and efficiency simulation (Section 3.2).

    All per-machine lists have the same length; index i of every list
    belongs to ``machine_ids[i]``.

    Attributes:
        machine_ids: Unique machine identifiers (list[str], at least one).
        working_hours: Daily working time per machine, hours/day (0 < x <= 24).
        cycle_time_sec: Cycle time per machine, seconds/unit (x > 0).
        base_efficiency_pct: Base efficiency per machine, % (0 < x <= 100).
        efficiency_min_pct: Lower efficiency bound, % (0 < x <= base).
        efficiency_max_pct: Upper efficiency bound, % (base <= x <= 100).
        days: Number of simulated days (1 <= x <= 3650).
        start_date: ISO date of day 0 (YYYY-MM-DD).
        seed: Random seed for ``np.random.default_rng`` (x >= 0).
    """

    def __init__(
        self,
        machine_ids: list,
        working_hours: list,
        cycle_time_sec: list,
        base_efficiency_pct: list,
        efficiency_min_pct: list,
        efficiency_max_pct: list,
        days: int = DEFAULT_DAYS,
        start_date: str = DEFAULT_START_DATE,
        seed: int = DEFAULT_SEED,
    ) -> None:
        """Initialize and validate the configuration.

        Raises:
            TypeError: If an argument has the wrong type.
            ValueError: If a value violates the Section 3.2 rules.
        """
        # -- machine_ids ----------------------------------------------------
        _validate_list(machine_ids, "machine_ids")
        if not machine_ids:
            raise ValueError("machine_ids en az bir makine içermelidir.")
        ids = [validate_non_empty_str(mid, "machine_id") for mid in machine_ids]
        if len(set(ids)) != len(ids):
            duplicates = sorted({mid for mid in ids if ids.count(mid) > 1})
            raise ValueError(f"machine_id değerleri benzersiz olmalıdır. Tekrarlanan: {duplicates}")
        machine_count = len(ids)

        # -- list types and lengths -----------------------------------------
        lists = {
            "working_hours": working_hours,
            "cycle_time_sec": cycle_time_sec,
            "base_efficiency_pct": base_efficiency_pct,
            "efficiency_min_pct": efficiency_min_pct,
            "efficiency_max_pct": efficiency_max_pct,
        }
        for name, values in lists.items():
            _validate_list(values, name)
            if len(values) != machine_count:
                raise ValueError(
                    f"{name} listesinin uzunluğu ({len(values)}) makine sayısıyla "
                    f"({machine_count}) aynı olmalıdır."
                )

        # -- per-machine numeric values -------------------------------------
        hours = [
            validate_number(v, "working_hours", lower=0, upper=24,
                            lower_inclusive=False, upper_inclusive=True)
            for v in working_hours
        ]
        cycles = [
            validate_number(v, "cycle_time_sec", lower=0, lower_inclusive=False)
            for v in cycle_time_sec
        ]
        bases = [
            validate_number(v, "base_efficiency_pct", lower=0, upper=100,
                            lower_inclusive=False, upper_inclusive=True)
            for v in base_efficiency_pct
        ]
        mins = [
            validate_number(v, "efficiency_min_pct", lower=0, lower_inclusive=False)
            for v in efficiency_min_pct
        ]
        maxs = [
            validate_number(v, "efficiency_max_pct", upper=100, upper_inclusive=True)
            for v in efficiency_max_pct
        ]
        for mid, base, low, high in zip(ids, bases, mins, maxs):
            if low > base:
                raise ValueError(
                    f"efficiency_min_pct, base_efficiency_pct değerinden büyük olamaz. "
                    f"(makine {mid}: {low} > {base})"
                )
            if high < base:
                raise ValueError(
                    f"efficiency_max_pct, base_efficiency_pct değerinden küçük olamaz. "
                    f"(makine {mid}: {high} < {base})"
                )

        # -- scalar values --------------------------------------------------
        self._days = _validate_int(days, "days", _MIN_DAYS, _MAX_DAYS)
        self._start_date = _validate_iso_date(start_date, "start_date")
        self._seed = _validate_int(seed, "seed", 0)

        # Stored as tuples so the configuration cannot be mutated from outside.
        self._machine_ids = tuple(ids)
        self._working_hours = tuple(hours)
        self._cycle_time_sec = tuple(cycles)
        self._base_efficiency_pct = tuple(bases)
        self._efficiency_min_pct = tuple(mins)
        self._efficiency_max_pct = tuple(maxs)

    # ------------------------------------------------------------------ #
    # Read-only properties (lists are returned as new copies)
    # ------------------------------------------------------------------ #

    @property
    def machine_ids(self) -> list:
        """Machine identifiers (list[str])."""
        return list(self._machine_ids)

    @property
    def working_hours(self) -> list:
        """Daily working time per machine in hours/day (list[float])."""
        return list(self._working_hours)

    @property
    def cycle_time_sec(self) -> list:
        """Cycle time per machine in seconds/unit (list[float])."""
        return list(self._cycle_time_sec)

    @property
    def base_efficiency_pct(self) -> list:
        """Base efficiency per machine in percent (list[float])."""
        return list(self._base_efficiency_pct)

    @property
    def efficiency_min_pct(self) -> list:
        """Lower daily efficiency bound per machine in percent (list[float])."""
        return list(self._efficiency_min_pct)

    @property
    def efficiency_max_pct(self) -> list:
        """Upper daily efficiency bound per machine in percent (list[float])."""
        return list(self._efficiency_max_pct)

    @property
    def days(self) -> int:
        """Number of simulated days."""
        return self._days

    @property
    def start_date(self) -> str:
        """ISO date (YYYY-MM-DD) of the first simulated day."""
        return self._start_date

    @property
    def seed(self) -> int:
        """Seed passed to ``np.random.default_rng``."""
        return self._seed

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def from_factory(
        cls,
        factory: dict,
        days: int = DEFAULT_DAYS,
        seed: int = DEFAULT_SEED,
        start_date: str = DEFAULT_START_DATE,
        efficiency_down_pct: float = EFFICIENCY_DOWN_PCT,
        efficiency_up_pct: float = EFFICIENCY_UP_PCT,
    ) -> 'SimulationConfig':
        """Build a configuration from a Mini Project 2 factory model.

        Only machines whose ``is_available()`` is True are used.  Machines
        are ordered by ``machine_id`` (same rule as MP3 generate_records).
        Efficiency bounds per machine:
        ``min = base - efficiency_down_pct`` and
        ``max = min(100, base + efficiency_up_pct)``.

        Args:
            factory: ``load_factory_json`` output (keys 'products',
                'machines', 'lines'; machines are Machine objects).
            days: Number of simulated days.
            seed: Random seed.
            start_date: ISO date of the first day.
            efficiency_down_pct: Distance of the minimum below the base (>= 0).
            efficiency_up_pct: Distance of the maximum above the base (>= 0).

        Returns:
            A validated SimulationConfig.

        Raises:
            TypeError: If *factory* is not a dict or a machine has no
                ``is_available`` method.
            ValueError: If no machine is available or a derived minimum
                efficiency is <= 0.
        """
        if not isinstance(factory, dict):
            raise TypeError("Fabrika verisi bir sözlük (dict) olmalıdır.")
        down = validate_number(efficiency_down_pct, "efficiency_down_pct", lower=0)
        up = validate_number(efficiency_up_pct, "efficiency_up_pct", lower=0)

        machines = factory.get("machines", [])
        for machine in machines:
            if not hasattr(machine, "is_available"):
                raise TypeError(
                    "Fabrika makineleri is_available() yöntemine sahip Machine nesneleri olmalıdır."
                )
        available = sorted(
            (m for m in machines if m.is_available()),
            key=lambda m: m.machine_id,
        )
        if not available:
            raise ValueError("Fabrikada üretime uygun (is_available) makine bulunmuyor.")

        bases = [m.efficiency_pct for m in available]
        mins = [base - down for base in bases]
        for machine, low in zip(available, mins):
            if low <= 0:
                raise ValueError(
                    f"Makine {machine.machine_id} için türetilen efficiency_min_pct "
                    f"({low}) sıfırdan büyük olmalıdır."
                )
        maxs = [min(100.0, base + up) for base in bases]

        return cls(
            machine_ids=[m.machine_id for m in available],
            working_hours=[m.working_hours for m in available],
            cycle_time_sec=[m.cycle_time_sec for m in available],
            base_efficiency_pct=bases,
            efficiency_min_pct=mins,
            efficiency_max_pct=maxs,
            days=days,
            start_date=start_date,
            seed=seed,
        )

    def get_machine_count(self) -> int:
        """Return the number of machines (M)."""
        return len(self._machine_ids)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return a JSON-compatible dict; keys equal the attribute names."""
        return {
            "machine_ids": self.machine_ids,
            "working_hours": self.working_hours,
            "cycle_time_sec": self.cycle_time_sec,
            "base_efficiency_pct": self.base_efficiency_pct,
            "efficiency_min_pct": self.efficiency_min_pct,
            "efficiency_max_pct": self.efficiency_max_pct,
            "days": self._days,
            "start_date": self._start_date,
            "seed": self._seed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SimulationConfig':
        """Create a SimulationConfig from a ``to_dict`` dictionary.

        Raises:
            TypeError: If *data* is not a dict.
            ValueError: If a required key is missing or a value is invalid.
        """
        if not isinstance(data, dict):
            raise TypeError("Yapılandırma verisi bir sözlük (dict) olmalıdır.")
        for field in _CONFIG_FIELDS:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")
        return cls(**{field: data[field] for field in _CONFIG_FIELDS})

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"SimulationConfig(machine_ids={self.machine_ids!r}, days={self._days}, "
            f"start_date={self._start_date!r}, seed={self._seed})"
        )


# ---------------------------------------------------------------------------
# SimulationResult
# ---------------------------------------------------------------------------

class SimulationResult:
    """Validated output of a simulation (Section 3.2; M machines, D days).

    Attributes:
        config: SimulationConfig used to produce the result.
        theoretical_capacity: float64 array of shape (M,), units/day.
        efficiency_pct: float64 array of shape (M, D), percent, inside each
            machine's [efficiency_min_pct, efficiency_max_pct] range.
        effective_capacity: float64 array of shape (M, D), units/day.
        planned_units: int64 array of shape (M, D), units, x >= 1.
        downtime_hours: float64 array of shape (M, D), hours,
            0 <= x <= machine working_hours.
        actual_units: int64 array of shape (M, D), units, x >= 0.

    Arrays are copied on construction, so later changes to the input
    arrays do not affect the result.
    """

    def __init__(
        self,
        config: SimulationConfig,
        theoretical_capacity: np.ndarray,
        efficiency_pct: np.ndarray,
        effective_capacity: np.ndarray,
        planned_units: np.ndarray,
        downtime_hours: np.ndarray,
        actual_units: np.ndarray,
    ) -> None:
        """Initialize and validate shapes, dtypes and ranges (Section 3.2).

        Raises:
            TypeError: If *config* is not a SimulationConfig, an argument is
                not an ``np.ndarray`` or has the wrong dtype.
            ValueError: If a shape or value range is invalid.
        """
        if not isinstance(config, SimulationConfig):
            raise TypeError("config bir SimulationConfig nesnesi olmalıdır.")

        arrays = {
            "theoretical_capacity": theoretical_capacity,
            "efficiency_pct": efficiency_pct,
            "effective_capacity": effective_capacity,
            "planned_units": planned_units,
            "downtime_hours": downtime_hours,
            "actual_units": actual_units,
        }
        machine_count = config.get_machine_count()
        matrix_shape = (machine_count, config.days)

        # -- types, dtypes and shapes ---------------------------------------
        for name, array in arrays.items():
            if not isinstance(array, np.ndarray):
                raise TypeError(f"{name} bir NumPy dizisi (np.ndarray) olmalıdır.")
            expected_dtype = np.float64 if name in _FLOAT_ARRAY_FIELDS else np.int64
            if array.dtype != expected_dtype:
                raise TypeError(
                    f"{name} dizisinin türü {np.dtype(expected_dtype).name} olmalıdır "
                    f"(verilen: {array.dtype})."
                )
            expected_shape = (machine_count,) if name == "theoretical_capacity" else matrix_shape
            if array.shape != expected_shape:
                raise ValueError(
                    f"{name} dizisinin şekli {expected_shape} olmalıdır (verilen: {array.shape})."
                )
            if name in _FLOAT_ARRAY_FIELDS and not np.all(np.isfinite(array)):
                raise ValueError(f"{name} dizisi NaN veya sonsuz değer içeremez.")

        # -- value ranges ---------------------------------------------------
        low = np.array(config.efficiency_min_pct, dtype=np.float64)[:, None]
        high = np.array(config.efficiency_max_pct, dtype=np.float64)[:, None]
        hours = np.array(config.working_hours, dtype=np.float64)[:, None]

        if np.any(theoretical_capacity <= 0):
            raise ValueError("theoretical_capacity değerleri sıfırdan büyük olmalıdır.")
        if np.any((efficiency_pct < low) | (efficiency_pct > high)):
            raise ValueError(
                "efficiency_pct değerleri her makinenin [efficiency_min_pct, "
                "efficiency_max_pct] aralığında olmalıdır."
            )
        if np.any(effective_capacity <= 0):
            raise ValueError("effective_capacity değerleri sıfırdan büyük olmalıdır.")
        if np.any(planned_units < 1):
            raise ValueError("planned_units değerleri en az 1 olmalıdır.")
        if np.any((downtime_hours < 0) | (downtime_hours > hours)):
            raise ValueError(
                "downtime_hours değerleri 0 ile makinenin working_hours değeri arasında olmalıdır."
            )
        if np.any(actual_units < 0):
            raise ValueError("actual_units değerleri negatif olamaz.")

        self._config = config
        self._theoretical_capacity = theoretical_capacity.copy()
        self._efficiency_pct = efficiency_pct.copy()
        self._effective_capacity = effective_capacity.copy()
        self._planned_units = planned_units.copy()
        self._downtime_hours = downtime_hours.copy()
        self._actual_units = actual_units.copy()

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #

    @property
    def config(self) -> SimulationConfig:
        """Configuration used to produce this result."""
        return self._config

    @property
    def theoretical_capacity(self) -> np.ndarray:
        """float64 array of shape (M,), units/day."""
        return self._theoretical_capacity

    @property
    def efficiency_pct(self) -> np.ndarray:
        """float64 array of shape (M, D), percent."""
        return self._efficiency_pct

    @property
    def effective_capacity(self) -> np.ndarray:
        """float64 array of shape (M, D), units/day."""
        return self._effective_capacity

    @property
    def planned_units(self) -> np.ndarray:
        """int64 array of shape (M, D), units."""
        return self._planned_units

    @property
    def downtime_hours(self) -> np.ndarray:
        """float64 array of shape (M, D), hours."""
        return self._downtime_hours

    @property
    def actual_units(self) -> np.ndarray:
        """int64 array of shape (M, D), units."""
        return self._actual_units

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def get_shape(self) -> tuple[int, int]:
        """Return the matrix shape (M, D) as plain ints."""
        return (self._config.get_machine_count(), self._config.days)

    def to_dict(self) -> dict:
        """Return a JSON-compatible dict; arrays become nested lists.

        Keys equal the attribute names; ``config`` is ``config.to_dict()``.
        """
        data = {"config": self._config.to_dict()}
        for name in _RESULT_ARRAY_FIELDS:
            data[name] = getattr(self, name).tolist()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'SimulationResult':
        """Create a SimulationResult from a ``to_dict`` dictionary.

        Raises:
            TypeError: If *data* is not a dict.
            ValueError: If a required key is missing or a value is invalid.
        """
        if not isinstance(data, dict):
            raise TypeError("Sonuç verisi bir sözlük (dict) olmalıdır.")
        for field in ("config",) + _RESULT_ARRAY_FIELDS:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")
        arrays = {}
        for name in _RESULT_ARRAY_FIELDS:
            dtype = np.float64 if name in _FLOAT_ARRAY_FIELDS else np.int64
            try:
                arrays[name] = np.array(data[name], dtype=dtype)
            except (TypeError, ValueError) as err:
                raise ValueError(f"{name} alanı sayısal bir diziye dönüştürülemedi.") from err
        return cls(config=SimulationConfig.from_dict(data["config"]), **arrays)

    def equals(self, other: 'SimulationResult') -> bool:
        """Return True if *other* has the same configuration and arrays.

        Arrays are compared with ``np.array_equal`` (exact equality).
        """
        if not isinstance(other, SimulationResult):
            return False
        if self._config.to_dict() != other.config.to_dict():
            return False
        return all(
            np.array_equal(getattr(self, name), getattr(other, name))
            for name in _RESULT_ARRAY_FIELDS
        )

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"SimulationResult(machine_ids={self._config.machine_ids!r}, "
            f"shape={self.get_shape()}, seed={self._config.seed})"
        )
