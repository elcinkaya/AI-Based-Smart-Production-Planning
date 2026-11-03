"""
test_models.py – Unit tests for constants, SimulationConfig and SimulationResult.

Covers valid/invalid configurations (Section 7.5), from_factory with the
MP2 sample factory (Section 7.3), to_dict/from_dict round trips and the
SimulationResult shape/dtype/range validation using the fixed 2x3 sample
(Section 7.2).  Test files never write to the real data/ folder.

Author: Kişi A
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from capacity_simulation import models
from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from capacity_simulation.models import SimulationConfig, SimulationResult
from factory_model.machine import Machine, MachineStatus
from factory_model.serialization import load_factory_json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_FACTORY_PATH = DATA_DIR / "sample_factory.json"
SIMULATION_CONFIG_PATH = DATA_DIR / "simulation_config.json"


def _valid_kwargs() -> dict:
    """Return keyword arguments of a valid two-machine configuration."""
    return {
        "machine_ids": ["M1", "M2"],
        "working_hours": [8.0, 16.0],
        "cycle_time_sec": [30.0, 45.0],
        "base_efficiency_pct": [85.0, 90.0],
        "efficiency_min_pct": [75.0, 80.0],
        "efficiency_max_pct": [90.0, 95.0],
    }


def _fixed_config() -> SimulationConfig:
    """Configuration of the fixed 2x3 sample (Section 7.2)."""
    return SimulationConfig(
        machine_ids=["M1", "M2"],
        working_hours=[8.0, 16.0],
        cycle_time_sec=[30.0, 45.0],
        base_efficiency_pct=[85.0, 90.0],
        efficiency_min_pct=[80.0, 90.0],
        efficiency_max_pct=[90.0, 100.0],
        days=3,
    )


def _fixed_arrays() -> dict:
    """Arrays of the fixed 2x3 sample (Section 7.2, hand-verified)."""
    return {
        "theoretical_capacity": np.array([960.0, 1280.0]),
        "efficiency_pct": np.array([[85.0, 80.0, 90.0], [90.0, 95.0, 100.0]]),
        "effective_capacity": np.array([[816.0, 768.0, 864.0], [1152.0, 1216.0, 1280.0]]),
        "planned_units": np.array([[816, 768, 432], [576, 1216, 1280]], dtype=np.int64),
        "downtime_hours": np.array([[0.0, 0.0, 2.0], [0.5, 0.0, 0.0]]),
        "actual_units": np.array([[816, 691, 324], [558, 1216, 1280]], dtype=np.int64),
    }


def _machine(machine_id: str, status: MachineStatus, efficiency_pct: float = 85.0) -> Machine:
    """Create a Machine for from_factory tests."""
    return Machine(
        machine_id=machine_id,
        name=f"Machine {machine_id}",
        working_hours=8.0,
        cycle_time_sec=30.0,
        efficiency_pct=efficiency_pct,
        maintenance_interval_hours=500.0,
        status=status,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    """Constants must match Section 3.2 (same numbers as MP3)."""

    def test_constant_values(self) -> None:
        self.assertEqual(models.DEFAULT_DAYS, 30)
        self.assertEqual(models.DEFAULT_SEED, 42)
        self.assertEqual(models.DEFAULT_START_DATE, "2026-10-01")
        self.assertEqual(models.EFFICIENCY_DOWN_PCT, 10.0)
        self.assertEqual(models.EFFICIENCY_UP_PCT, 5.0)
        self.assertEqual(models.LOAD_FACTOR_RANGE, (0.80, 1.00))
        self.assertEqual(models.PERFORMANCE_FACTOR_RANGE, (0.90, 1.05))
        self.assertEqual(models.DOWNTIME_PROBABILITY, 0.30)
        self.assertEqual(models.DOWNTIME_HOURS_RANGE, (0.25, 3.0))
        self.assertEqual(models.DOWNTIME_STEP_HOURS, 0.25)


# ---------------------------------------------------------------------------
# SimulationConfig – valid input
# ---------------------------------------------------------------------------

class TestSimulationConfigValid(unittest.TestCase):
    """Valid configurations and boundary values."""

    def test_valid_config_with_defaults(self) -> None:
        config = SimulationConfig(**_valid_kwargs())
        self.assertEqual(config.machine_ids, ["M1", "M2"])
        self.assertEqual(config.working_hours, [8.0, 16.0])
        self.assertEqual(config.cycle_time_sec, [30.0, 45.0])
        self.assertEqual(config.base_efficiency_pct, [85.0, 90.0])
        self.assertEqual(config.efficiency_min_pct, [75.0, 80.0])
        self.assertEqual(config.efficiency_max_pct, [90.0, 95.0])
        self.assertEqual(config.days, 30)
        self.assertEqual(config.start_date, "2026-10-01")
        self.assertEqual(config.seed, 42)
        self.assertEqual(config.get_machine_count(), 2)

    def test_int_values_are_stored_as_float(self) -> None:
        kwargs = _valid_kwargs()
        kwargs["working_hours"] = [8, 16]
        config = SimulationConfig(**kwargs)
        self.assertEqual(config.working_hours, [8.0, 16.0])
        self.assertTrue(all(isinstance(v, float) for v in config.working_hours))

    def test_boundary_values_are_accepted(self) -> None:
        config = SimulationConfig(
            machine_ids=["M1"],
            working_hours=[24.0],
            cycle_time_sec=[0.5],
            base_efficiency_pct=[100.0],
            efficiency_min_pct=[100.0],   # min == base
            efficiency_max_pct=[100.0],   # max == base == 100
            days=3650,
            seed=0,
        )
        self.assertEqual(config.days, 3650)
        self.assertEqual(config.seed, 0)
        self.assertEqual(SimulationConfig(**_valid_kwargs(), days=1).days, 1)

    def test_lists_cannot_be_mutated_from_outside(self) -> None:
        kwargs = _valid_kwargs()
        config = SimulationConfig(**kwargs)
        kwargs["working_hours"][0] = 99.0
        config.working_hours[0] = 99.0
        config.machine_ids.append("M9")
        self.assertEqual(config.working_hours, [8.0, 16.0])
        self.assertEqual(config.machine_ids, ["M1", "M2"])

    def test_repr(self) -> None:
        text = repr(SimulationConfig(**_valid_kwargs()))
        self.assertTrue(text.startswith("SimulationConfig("))
        self.assertIn("'M1'", text)
        self.assertIn("seed=42", text)


# ---------------------------------------------------------------------------
# SimulationConfig – invalid input (Section 7.5)
# ---------------------------------------------------------------------------

class TestSimulationConfigInvalid(unittest.TestCase):
    """Invalid configurations raise ValueError/TypeError with Turkish messages."""

    def _assert_value_error(self, message_part: str, **changes) -> None:
        kwargs = _valid_kwargs()
        kwargs.update(changes)
        with self.assertRaises(ValueError) as ctx:
            SimulationConfig(**kwargs)
        self.assertIn(message_part, str(ctx.exception))

    def test_empty_machine_list(self) -> None:
        self._assert_value_error(
            "en az bir makine",
            machine_ids=[], working_hours=[], cycle_time_sec=[], base_efficiency_pct=[],
            efficiency_min_pct=[], efficiency_max_pct=[],
        )

    def test_list_lengths_differ(self) -> None:
        self._assert_value_error("uzunluğu", working_hours=[8.0])
        self._assert_value_error("uzunluğu", efficiency_max_pct=[90.0, 95.0, 99.0])

    def test_duplicate_machine_id(self) -> None:
        self._assert_value_error("benzersiz", machine_ids=["M1", "M1"])

    def test_empty_machine_id(self) -> None:
        self._assert_value_error("boş olamaz", machine_ids=["M1", "  "])

    def test_cycle_time_zero(self) -> None:
        self._assert_value_error("cycle_time_sec", cycle_time_sec=[0, 45.0])

    def test_working_hours_out_of_range(self) -> None:
        self._assert_value_error("working_hours", working_hours=[25, 16.0])
        self._assert_value_error("working_hours", working_hours=[0, 16.0])

    def test_base_efficiency_out_of_range(self) -> None:
        self._assert_value_error("base_efficiency_pct", base_efficiency_pct=[0, 90.0])
        self._assert_value_error("base_efficiency_pct", base_efficiency_pct=[101, 90.0])

    def test_efficiency_min_greater_than_base(self) -> None:
        self._assert_value_error(
            "efficiency_min_pct, base_efficiency_pct değerinden büyük olamaz.",
            efficiency_min_pct=[86.0, 80.0],
        )

    def test_efficiency_min_not_positive(self) -> None:
        self._assert_value_error("efficiency_min_pct", efficiency_min_pct=[0, 80.0])

    def test_efficiency_max_greater_than_100(self) -> None:
        self._assert_value_error("efficiency_max_pct", efficiency_max_pct=[101.0, 95.0])

    def test_efficiency_max_less_than_base(self) -> None:
        self._assert_value_error(
            "efficiency_max_pct, base_efficiency_pct değerinden küçük olamaz.",
            efficiency_max_pct=[84.0, 95.0],
        )

    def test_days_out_of_range(self) -> None:
        self._assert_value_error("days", days=0)
        self._assert_value_error("days", days=3651)

    def test_negative_seed(self) -> None:
        self._assert_value_error("seed", seed=-1)

    def test_invalid_start_date(self) -> None:
        self._assert_value_error("start_date", start_date="2026-13-40")
        self._assert_value_error("start_date", start_date="20261001")
        self._assert_value_error("start_date", start_date="01.10.2026")

    def test_wrong_types_raise_type_error(self) -> None:
        cases = [
            {"machine_ids": ("M1", "M2")},
            {"machine_ids": ["M1", 2]},
            {"working_hours": "8,16"},
            {"working_hours": ["8", 16.0]},
            {"cycle_time_sec": [True, 45.0]},
            {"days": 30.0},
            {"days": True},
            {"seed": "42"},
            {"start_date": 20261001},
        ]
        for change in cases:
            with self.subTest(change=change):
                kwargs = _valid_kwargs()
                kwargs.update(change)
                with self.assertRaises(TypeError):
                    SimulationConfig(**kwargs)


# ---------------------------------------------------------------------------
# SimulationConfig.from_factory
# ---------------------------------------------------------------------------

class TestFromFactory(unittest.TestCase):
    """from_factory derives the machine set and ranges from the MP2 factory."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(str(SAMPLE_FACTORY_PATH))

    def test_sample_factory_matches_section_7_3(self) -> None:
        config = SimulationConfig.from_factory(self.factory)
        self.assertEqual(config.machine_ids, ["M1", "M2", "M3", "M5"])  # M4 is broken
        self.assertEqual(config.working_hours, [8.0, 16.0, 8.0, 8.0])
        self.assertEqual(config.cycle_time_sec, [30.0, 45.0, 60.0, 30.0])
        self.assertEqual(config.base_efficiency_pct, [85.0, 90.0, 70.0, 80.0])
        self.assertEqual(config.efficiency_min_pct, [75.0, 80.0, 60.0, 70.0])
        self.assertEqual(config.efficiency_max_pct, [90.0, 95.0, 75.0, 85.0])
        self.assertEqual(config.days, 30)
        self.assertEqual(config.seed, 42)
        self.assertEqual(config.start_date, "2026-10-01")

    def test_theoretical_capacity_of_sample_factory(self) -> None:
        config = SimulationConfig.from_factory(self.factory)
        theoretical = calculate_theoretical_capacity_array(
            np.array(config.working_hours), np.array(config.cycle_time_sec)
        )
        self.assertTrue(np.allclose(theoretical, [960.0, 1280.0, 480.0, 960.0]))

    def test_only_available_machines_are_used(self) -> None:
        available_ids = sorted(
            m.machine_id for m in self.factory["machines"] if m.is_available()
        )
        config = SimulationConfig.from_factory(self.factory)
        self.assertEqual(config.machine_ids, available_ids)

    def test_custom_parameters(self) -> None:
        config = SimulationConfig.from_factory(
            self.factory, days=120, seed=7, start_date="2027-01-01",
            efficiency_down_pct=5.0, efficiency_up_pct=20.0,
        )
        self.assertEqual(config.days, 120)
        self.assertEqual(config.seed, 7)
        self.assertEqual(config.start_date, "2027-01-01")
        self.assertEqual(config.efficiency_min_pct, [80.0, 85.0, 65.0, 75.0])
        self.assertEqual(config.efficiency_max_pct, [100.0, 100.0, 90.0, 100.0])

    def test_max_is_clamped_to_100(self) -> None:
        factory = {"machines": [_machine("M1", MachineStatus.IDLE, efficiency_pct=98.0)]}
        config = SimulationConfig.from_factory(factory)
        self.assertEqual(config.efficiency_min_pct, [88.0])
        self.assertEqual(config.efficiency_max_pct, [100.0])

    def test_machines_are_sorted_by_id(self) -> None:
        factory = {"machines": [
            _machine("M3", MachineStatus.RUNNING),
            _machine("M1", MachineStatus.IDLE),
        ]}
        self.assertEqual(SimulationConfig.from_factory(factory).machine_ids, ["M1", "M3"])

    def test_factory_without_available_machine(self) -> None:
        factory = {"machines": [
            _machine("M1", MachineStatus.BROKEN),
            _machine("M2", MachineStatus.MAINTENANCE),
        ]}
        with self.assertRaises(ValueError) as ctx:
            SimulationConfig.from_factory(factory)
        self.assertIn("uygun", str(ctx.exception))
        with self.assertRaises(ValueError):
            SimulationConfig.from_factory({"products": [], "machines": [], "lines": []})

    def test_derived_min_efficiency_not_positive(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            SimulationConfig.from_factory(self.factory, efficiency_down_pct=70.0)
        self.assertIn("efficiency_min_pct", str(ctx.exception))

    def test_invalid_factory_type(self) -> None:
        with self.assertRaises(TypeError):
            SimulationConfig.from_factory(list(self.factory["machines"]))
        with self.assertRaises(TypeError):
            SimulationConfig.from_factory({"machines": [{"machine_id": "M1"}]})

    def test_invalid_scalar_parameters(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig.from_factory(self.factory, days=0)
        with self.assertRaises(ValueError):
            SimulationConfig.from_factory(self.factory, seed=-5)
        with self.assertRaises(ValueError):
            SimulationConfig.from_factory(self.factory, efficiency_down_pct=-1.0)

    def test_simulation_config_json_matches_from_factory(self) -> None:
        with open(SIMULATION_CONFIG_PATH, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        self.assertEqual(stored, SimulationConfig.from_factory(self.factory).to_dict())
        self.assertEqual(SimulationConfig.from_dict(stored).machine_ids, ["M1", "M2", "M3", "M5"])


# ---------------------------------------------------------------------------
# SimulationConfig serialization
# ---------------------------------------------------------------------------

class TestSimulationConfigSerialization(unittest.TestCase):
    """to_dict / from_dict round trip."""

    def test_to_dict_keys_equal_attribute_names(self) -> None:
        data = SimulationConfig(**_valid_kwargs()).to_dict()
        self.assertEqual(
            list(data.keys()),
            ["machine_ids", "working_hours", "cycle_time_sec", "base_efficiency_pct",
             "efficiency_min_pct", "efficiency_max_pct", "days", "start_date", "seed"],
        )

    def test_round_trip_through_json(self) -> None:
        original = SimulationConfig(**_valid_kwargs(), days=45, start_date="2026-11-15", seed=3)
        restored = SimulationConfig.from_dict(json.loads(json.dumps(original.to_dict())))
        self.assertEqual(restored.to_dict(), original.to_dict())

    def test_from_dict_missing_key(self) -> None:
        data = SimulationConfig(**_valid_kwargs()).to_dict()
        del data["seed"]
        with self.assertRaises(ValueError) as ctx:
            SimulationConfig.from_dict(data)
        self.assertIn("Eksik alan: seed", str(ctx.exception))

    def test_from_dict_invalid_value(self) -> None:
        data = SimulationConfig(**_valid_kwargs()).to_dict()
        data["days"] = 0
        with self.assertRaises(ValueError):
            SimulationConfig.from_dict(data)

    def test_from_dict_requires_dict(self) -> None:
        with self.assertRaises(TypeError):
            SimulationConfig.from_dict([("machine_ids", ["M1"])])


# ---------------------------------------------------------------------------
# SimulationResult
# ---------------------------------------------------------------------------

class TestSimulationResult(unittest.TestCase):
    """SimulationResult with the fixed 2x3 sample (Section 7.2)."""

    def setUp(self) -> None:
        self.config = _fixed_config()
        self.arrays = _fixed_arrays()

    def _build(self, **changes) -> SimulationResult:
        arrays = dict(self.arrays)
        arrays.update(changes)
        return SimulationResult(self.config, **arrays)

    def test_valid_result(self) -> None:
        result = self._build()
        self.assertEqual(result.get_shape(), (2, 3))
        self.assertIs(result.config, self.config)
        for name, array in self.arrays.items():
            self.assertTrue(np.array_equal(getattr(result, name), array))
        self.assertEqual(result.planned_units.dtype, np.int64)
        self.assertEqual(result.efficiency_pct.dtype, np.float64)

    def test_fixed_sample_is_consistent_with_capacity_functions(self) -> None:
        theoretical = calculate_theoretical_capacity_array(
            np.array(self.config.working_hours), np.array(self.config.cycle_time_sec)
        )
        effective = calculate_effective_capacity_array(theoretical, self.arrays["efficiency_pct"])
        result = self._build(theoretical_capacity=theoretical, effective_capacity=effective)
        self.assertTrue(np.allclose(result.theoretical_capacity, [960.0, 1280.0]))
        self.assertTrue(np.allclose(result.effective_capacity, self.arrays["effective_capacity"]))

    def test_arrays_are_copied(self) -> None:
        arrays = _fixed_arrays()
        result = SimulationResult(self.config, **arrays)
        arrays["actual_units"][0, 0] = 0
        self.assertEqual(result.actual_units[0, 0], 816)

    def test_to_dict_is_json_compatible(self) -> None:
        data = self._build().to_dict()
        self.assertEqual(
            list(data.keys()),
            ["config", "theoretical_capacity", "efficiency_pct", "effective_capacity",
             "planned_units", "downtime_hours", "actual_units"],
        )
        self.assertEqual(data["config"], self.config.to_dict())
        self.assertEqual(data["planned_units"], [[816, 768, 432], [576, 1216, 1280]])
        self.assertIsInstance(data["planned_units"][0][0], int)
        self.assertIsInstance(data["downtime_hours"][0][0], float)
        json.dumps(data)  # must not raise

    def test_from_dict_round_trip(self) -> None:
        original = self._build()
        restored = SimulationResult.from_dict(json.loads(json.dumps(original.to_dict())))
        self.assertTrue(original.equals(restored))

    def test_from_dict_missing_key(self) -> None:
        data = self._build().to_dict()
        del data["actual_units"]
        with self.assertRaises(ValueError):
            SimulationResult.from_dict(data)

    def test_equals(self) -> None:
        result = self._build()
        self.assertTrue(result.equals(SimulationResult(self.config, **_fixed_arrays())))
        changed = self.arrays["actual_units"].copy()
        changed[1, 2] = 1279
        self.assertFalse(result.equals(self._build(actual_units=changed)))
        other_config = SimulationConfig.from_dict({**self.config.to_dict(), "seed": 43})
        self.assertFalse(result.equals(SimulationResult(other_config, **self.arrays)))
        self.assertFalse(result.equals("not a result"))

    def test_repr(self) -> None:
        text = repr(self._build())
        self.assertTrue(text.startswith("SimulationResult("))
        self.assertIn("(2, 3)", text)

    # -- invalid input ------------------------------------------------------

    def test_config_type(self) -> None:
        with self.assertRaises(TypeError):
            SimulationResult(self.config.to_dict(), **self.arrays)

    def test_non_array_input(self) -> None:
        with self.assertRaises(TypeError):
            self._build(planned_units=[[816, 768, 432], [576, 1216, 1280]])

    def test_wrong_dtype(self) -> None:
        with self.assertRaises(TypeError):
            self._build(planned_units=self.arrays["planned_units"].astype(np.float64))
        with self.assertRaises(TypeError):
            self._build(efficiency_pct=self.arrays["efficiency_pct"].astype(np.int64))
        with self.assertRaises(TypeError):
            self._build(actual_units=self.arrays["actual_units"].astype(np.int32))

    def test_wrong_shape(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self._build(efficiency_pct=self.arrays["efficiency_pct"][:, :2])
        self.assertIn("şekli", str(ctx.exception))
        with self.assertRaises(ValueError):
            self._build(theoretical_capacity=np.array([960.0, 1280.0, 480.0]))
        with self.assertRaises(ValueError):
            self._build(downtime_hours=self.arrays["downtime_hours"].T.copy())

    def test_efficiency_outside_machine_range(self) -> None:
        efficiency = self.arrays["efficiency_pct"].copy()
        efficiency[0, 0] = 79.0  # M1 range is [80, 90]
        with self.assertRaises(ValueError):
            self._build(efficiency_pct=efficiency)

    def test_planned_units_below_one(self) -> None:
        planned = self.arrays["planned_units"].copy()
        planned[0, 1] = 0
        with self.assertRaises(ValueError):
            self._build(planned_units=planned)

    def test_downtime_out_of_range(self) -> None:
        downtime = self.arrays["downtime_hours"].copy()
        downtime[0, 0] = 8.25  # M1 works 8 hours
        with self.assertRaises(ValueError):
            self._build(downtime_hours=downtime)
        downtime[0, 0] = -0.25
        with self.assertRaises(ValueError):
            self._build(downtime_hours=downtime)

    def test_downtime_equal_to_working_hours_is_allowed(self) -> None:
        downtime = self.arrays["downtime_hours"].copy()
        downtime[1, 1] = 16.0
        actual = self.arrays["actual_units"].copy()
        actual[1, 1] = 0
        result = self._build(downtime_hours=downtime, actual_units=actual)
        self.assertEqual(result.actual_units[1, 1], 0)

    def test_negative_actual_units(self) -> None:
        actual = self.arrays["actual_units"].copy()
        actual[0, 0] = -1
        with self.assertRaises(ValueError):
            self._build(actual_units=actual)

    def test_non_finite_values(self) -> None:
        effective = self.arrays["effective_capacity"].copy()
        effective[0, 0] = np.nan
        with self.assertRaises(ValueError):
            self._build(effective_capacity=effective)

    def test_non_positive_capacity(self) -> None:
        with self.assertRaises(ValueError):
            self._build(theoretical_capacity=np.array([0.0, 1280.0]))


if __name__ == "__main__":
    unittest.main()
