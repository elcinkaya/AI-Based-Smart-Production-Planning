"""
test_simulation.py – Golden values and property tests for simulate().

Covers (Section 7.3):
- golden values for seed 42, MP2 sample factory, 30 days (NumPy 2.4.4),
- SimulationResult consistency: planned_units <= ceil(effective_capacity),
  planned_units >= 1, efficiency inside each machine range, downtime
  quarter hours <= working_hours, actual_units >= 0,
- same seed -> equals() True, seed 43 -> False,
- configuration is not modified by simulate,
- planned_units below 1 raises ValueError (Section 7.5).

Totals are computed here with plain NumPy only to check the golden values;
the official summary dictionary belongs to stats.py (Kişi C).

Author: Kişi B
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from capacity_simulation.generation import simulate
from capacity_simulation.models import SimulationConfig, SimulationResult
from factory_model.serialization import load_factory_json

SAMPLE_FACTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_factory.json"
REFERENCE_NUMPY_VERSION = "2.4.4"


def _golden_config(seed: int = 42, days: int = 30) -> SimulationConfig:
    """Return SimulationConfig.from_factory for the MP2 sample factory."""
    return SimulationConfig.from_factory(load_factory_json(str(SAMPLE_FACTORY_PATH)), days=days, seed=seed)


class TestGoldenValues(unittest.TestCase):
    """Section 7.3 golden values (seed 42, sample factory, 30 days)."""

    @classmethod
    def setUpClass(cls):
        cls.config = _golden_config()
        cls.result = simulate(cls.config)

    def test_numpy_version(self):
        self.assertEqual(
            np.__version__, REFERENCE_NUMPY_VERSION,
            f"Altın değerler NumPy {REFERENCE_NUMPY_VERSION} ile üretilmiştir "
            f"(kurulu sürüm: {np.__version__}).")

    def test_config_from_factory(self):
        cfg = self.config
        self.assertEqual(cfg.machine_ids, ["M1", "M2", "M3", "M5"])
        self.assertEqual(cfg.working_hours, [8, 16, 8, 8])
        self.assertEqual(cfg.cycle_time_sec, [30, 45, 60, 30])
        self.assertEqual(cfg.base_efficiency_pct, [85, 90, 70, 80])
        self.assertEqual(cfg.efficiency_min_pct, [75, 80, 60, 70])
        self.assertEqual(cfg.efficiency_max_pct, [90, 95, 75, 85])
        self.assertEqual((cfg.days, cfg.seed), (30, 42))

    def test_result_type_and_shape(self):
        self.assertIsInstance(self.result, SimulationResult)
        self.assertEqual(self.result.get_shape(), (4, 30))
        self.assertEqual(self.result.efficiency_pct.shape, (4, 30))
        self.assertEqual(self.result.theoretical_capacity.shape, (4,))

    def test_dtypes(self):
        r = self.result
        for name in ("theoretical_capacity", "efficiency_pct", "effective_capacity", "downtime_hours"):
            self.assertEqual(getattr(r, name).dtype, np.float64, name)
        for name in ("planned_units", "actual_units"):
            self.assertEqual(getattr(r, name).dtype, np.int64, name)

    def test_theoretical_capacity(self):
        self.assertTrue(np.allclose(self.result.theoretical_capacity, [960, 1280, 480, 960]))

    def test_production_totals(self):
        planned = int(self.result.planned_units.sum())
        actual = int(self.result.actual_units.sum())
        self.assertEqual(planned, 80449)
        self.assertEqual(actual, 73774)
        self.assertEqual(actual - planned, -6675)
        self.assertAlmostEqual(actual / planned * 100, 91.70, delta=0.01)
        self.assertFalse(actual >= planned)  # plan_met False

    def test_downtime(self):
        downtime = self.result.downtime_hours
        self.assertAlmostEqual(float(downtime.sum()), 65.25, delta=0.01)
        self.assertEqual(int(np.count_nonzero(downtime)), 37)
        total_hours = sum(self.config.working_hours) * self.config.days
        self.assertAlmostEqual(total_hours, 1200, delta=0.01)
        availability = (total_hours - float(downtime.sum())) / total_hours * 100
        self.assertAlmostEqual(availability, 94.56, delta=0.01)

    def test_planned_min(self):
        self.assertEqual(int(self.result.planned_units.min()), 233)

    def test_efficiency_mean(self):
        self.assertAlmostEqual(float(self.result.efficiency_pct.mean()), 78.73, delta=0.01)

    def test_effective_capacity_statistics(self):
        ec = self.result.effective_capacity
        self.assertAlmostEqual(float(ec.mean()), 745.57, delta=0.01)
        self.assertAlmostEqual(float(ec.std(ddof=0)), 286.24, delta=0.01)
        self.assertAlmostEqual(float(ec.min()), 289.64, delta=0.01)
        self.assertAlmostEqual(float(ec.max()), 1209.76, delta=0.01)
        self.assertTrue(np.allclose(ec.mean(axis=1), [800.52, 1116.25, 320.03, 745.49], atol=0.01))


class TestSimulationProperties(unittest.TestCase):
    """Seed independent properties (must hold for every run)."""

    SEEDS = (0, 1, 42, 43, 2026)

    def test_same_seed_equal_results(self):
        self.assertTrue(simulate(_golden_config(42)).equals(simulate(_golden_config(42))))

    def test_different_seed_different_results(self):
        self.assertFalse(simulate(_golden_config(42)).equals(simulate(_golden_config(43))))

    def test_properties_for_several_seeds(self):
        for seed in self.SEEDS:
            with self.subTest(seed=seed):
                cfg = _golden_config(seed=seed, days=60)
                r = simulate(cfg)
                low = np.array(cfg.efficiency_min_pct)[:, None]
                high = np.array(cfg.efficiency_max_pct)[:, None]
                hours = np.array(cfg.working_hours)[:, None]
                self.assertTrue(np.all((r.efficiency_pct >= low) & (r.efficiency_pct <= high)))
                self.assertTrue(np.all(r.planned_units <= np.ceil(r.effective_capacity)))
                self.assertTrue(np.all(r.planned_units >= 1))
                self.assertTrue(np.array_equal(r.downtime_hours * 4, np.rint(r.downtime_hours * 4)))
                self.assertTrue(np.all((r.downtime_hours >= 0) & (r.downtime_hours <= hours)))
                self.assertTrue(np.all(r.actual_units >= 0))

    def test_full_downtime_gives_zero_actual(self):
        # Working hours of 0.25 h: every downtime cell is capped at 0.25 h.
        cfg = SimulationConfig(
            machine_ids=["X1"], working_hours=[0.25], cycle_time_sec=[1.0],
            base_efficiency_pct=[80.0], efficiency_min_pct=[70.0],
            efficiency_max_pct=[85.0], days=200, seed=5)
        r = simulate(cfg)
        full = r.downtime_hours == 0.25
        self.assertTrue(np.any(full))
        self.assertTrue(np.all(r.actual_units[full] == 0))

    def test_config_not_modified(self):
        cfg = _golden_config()
        before = cfg.to_dict()
        result = simulate(cfg)
        self.assertEqual(cfg.to_dict(), before)
        self.assertIs(result.config, cfg)

    def test_planned_below_one_raises(self):
        cfg = SimulationConfig(
            machine_ids=["X1"], working_hours=[8.0], cycle_time_sec=[100000.0],
            base_efficiency_pct=[80.0], efficiency_min_pct=[70.0],
            efficiency_max_pct=[85.0], days=5, seed=42)
        with self.assertRaises(ValueError):
            simulate(cfg)

    def test_wrong_config_type_raises(self):
        with self.assertRaises(TypeError):
            simulate({"seed": 42})


if __name__ == "__main__":
    unittest.main()
