"""
test_integration.py - MP1 and MP3 integration and bridge scenarios.

Covers all scenarios of Section 7.1, 7.3, 7.4 and 7.5:
- Scenario 1: Section 7.1 vectorized capacity vs. MP1 scalar loop
- Scenario 3-7: Fixed 2x3 example -> simulation_to_records (9 records),
  preserve totals, M2 day 1 split, M1 product rotation (P-A, P-B, P-A),
  RecordStore.add_records + MP3 summarize_records == summarize_simulation
- Scenario 8: Golden config (seed 42, 30 days) -> 150 records (30+60+30+30)
  with identical totals to Section 7.3
- Scenario 9: days=120 -> 600 records (MP5 target)
- Scenario 10: working_hours=10 -> ValueError (non-integer shift count)
- Scenario 13: compare_loop_and_numpy results_match True
- Section 7.5: TypeError when factory is not a dict; ValueError when a shift
  would receive 0 planned units.

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

from capacity_simulation.benchmark import build_benchmark_report, compare_loop_and_numpy
from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from capacity_simulation.export import simulation_to_records
from capacity_simulation.generation import simulate
from capacity_simulation.models import SimulationConfig, SimulationResult
from capacity_simulation.stats import summarize_simulation
from factory_model import calculations as mp1
from factory_model.serialization import load_factory_json
from production_records.analysis import summarize_records
from production_records.record import Shift
from production_records.record_store import RecordStore
from tests.test_stats import build_fixed_result

SAMPLE_FACTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_factory.json"


class TestMp1VectorizedCompatibility(unittest.TestCase):
    """Section 7.1 and Section 7.4 scenario 1."""

    def test_mp1_scenarios_match_loop(self) -> None:
        working_hours = np.array([8.0, 16.0, 8.0, 10.0, 8.0])
        cycle_time_sec = np.array([30.0, 45.0, 60.0, 20.0, 30.0])
        efficiency_pct = np.array([[85.0], [90.0], [70.0], [95.0], [80.0]])

        theo_vec = calculate_theoretical_capacity_array(working_hours, cycle_time_sec)
        eff_vec = calculate_effective_capacity_array(theo_vec, efficiency_pct)

        theo_loop = np.array([
            mp1.theoretical_capacity(w, c)
            for w, c in zip(working_hours.tolist(), cycle_time_sec.tolist())
        ])
        eff_loop = np.array([
            [mp1.effective_capacity(t, e) for e in row]
            for t, row in zip(theo_loop.tolist(), efficiency_pct.tolist())
        ])

        self.assertTrue(np.allclose(theo_vec, [960, 1280, 480, 1800, 960]))
        self.assertTrue(np.allclose(eff_vec.ravel(), [816, 1152, 336, 1710, 768]))
        self.assertTrue(np.allclose(theo_vec, theo_loop))
        self.assertTrue(np.allclose(eff_vec, eff_loop))


class TestMp3BridgeScenarios(unittest.TestCase):
    """Section 7.4 scenarios 3 through 10 and Section 7.5 bridge errors."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(str(SAMPLE_FACTORY_PATH))

    def test_scenarios_3_4_5_6_fixed_example_to_records(self) -> None:
        result = build_fixed_result()
        records = simulation_to_records(result, self.factory)

        # Scenario 3: 9 records (M1: 3, M2: 6), unique keys, record_id is None
        self.assertEqual(len(records), 9)
        counts = Counter(r.machine_id for r in records)
        self.assertEqual(counts["M1"], 3)
        self.assertEqual(counts["M2"], 6)
        keys = [r.get_key() for r in records]
        self.assertEqual(len(set(keys)), 9)
        self.assertTrue(all(r.record_id is None for r in records))

        # Scenario 4: totals preserved
        self.assertEqual(sum(r.planned_units for r in records), 5088)
        self.assertEqual(sum(r.actual_units for r in records), 4885)
        self.assertAlmostEqual(sum(r.downtime_hours for r in records), 2.5, delta=0.01)

        # Scenario 5: M2 day 1 (planned 576, actual 558, downtime 0.5) -> 2 shifts
        m2_day1 = [
            r for r in records
            if r.machine_id == "M2" and r.production_date.isoformat() == "2026-10-01"
        ]
        self.assertEqual(len(m2_day1), 2)
        self.assertEqual([r.shift for r in m2_day1], [Shift.MORNING, Shift.AFTERNOON])
        for rec in m2_day1:
            self.assertEqual(rec.planned_units, 288)
            self.assertEqual(rec.actual_units, 279)
            self.assertAlmostEqual(rec.downtime_hours, 0.25)

        # Scenario 6: M1 products on days 1, 2, 3 -> P-A, P-B, P-A
        m1_products = [r.product_code for r in records if r.machine_id == "M1"]
        self.assertEqual(m1_products, ["P-A", "P-B", "P-A"])

    def test_scenario_7_record_store_and_mp3_summarize_match_simulation(self) -> None:
        result = build_fixed_result()
        records = simulation_to_records(result, self.factory)
        sim_summary = summarize_simulation(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "records.csv")
            store = RecordStore(csv_path)
            added = store.add_records(records)
            self.assertEqual(len(added), 9)
            self.assertEqual([r.record_id for r in added], list(range(1, 10)))

            mp3_summary = summarize_records(store.get_all())

        self.assertEqual(mp3_summary["record_count"], 9)
        self.assertEqual(mp3_summary["date_from"], sim_summary["date_from"])
        self.assertEqual(mp3_summary["date_to"], sim_summary["date_to"])
        self.assertEqual(mp3_summary["total_planned_units"], 5088)
        self.assertEqual(mp3_summary["total_actual_units"], 4885)
        self.assertEqual(mp3_summary["production_gap"], -203)
        self.assertAlmostEqual(mp3_summary["attainment_pct"], 96.01, delta=0.01)
        self.assertAlmostEqual(mp3_summary["total_downtime_hours"], 2.5, delta=0.01)
        self.assertAlmostEqual(mp3_summary["availability_pct"], 96.53, delta=0.01)
        self.assertEqual(mp3_summary["plan_met"], sim_summary["plan_met"])
        self.assertEqual(mp3_summary["status_message"], sim_summary["status_message"])

    def test_scenario_8_golden_30_days_produces_150_records(self) -> None:
        config = SimulationConfig.from_factory(self.factory, days=30, seed=42)
        result = simulate(config)
        records = simulation_to_records(result, self.factory)

        self.assertEqual(len(records), 150)
        counts = Counter(r.machine_id for r in records)
        self.assertEqual(counts, {"M1": 30, "M2": 60, "M3": 30, "M5": 30})
        self.assertEqual(len({r.get_key() for r in records}), 150)

        sim_summary = summarize_simulation(result)
        mp3_summary = summarize_records(records)
        self.assertEqual(mp3_summary["total_planned_units"], 80449)
        self.assertEqual(mp3_summary["total_actual_units"], 73774)
        self.assertEqual(mp3_summary["production_gap"], -6675)
        self.assertAlmostEqual(mp3_summary["attainment_pct"], 91.70, delta=0.01)
        self.assertAlmostEqual(mp3_summary["total_downtime_hours"], 65.25, delta=0.01)
        self.assertAlmostEqual(mp3_summary["availability_pct"], 94.56, delta=0.01)
        self.assertEqual(mp3_summary["status_message"], sim_summary["status_message"])

    def test_scenario_9_days_120_produces_600_records(self) -> None:
        config = SimulationConfig.from_factory(self.factory, days=120, seed=42)
        result = simulate(config)
        records = simulation_to_records(result, self.factory)
        self.assertEqual(len(records), 600)

    def test_scenario_10_non_integer_shift_count_raises_value_error(self) -> None:
        config = SimulationConfig(
            machine_ids=["M1"],
            working_hours=[10.0],
            cycle_time_sec=[30.0],
            base_efficiency_pct=[85.0],
            efficiency_min_pct=[75.0],
            efficiency_max_pct=[90.0],
            days=1,
        )
        result = SimulationResult(
            config=config,
            theoretical_capacity=np.array([1200.0]),
            efficiency_pct=np.array([[85.0]]),
            effective_capacity=np.array([[1020.0]]),
            planned_units=np.array([[900]], dtype=np.int64),
            downtime_hours=np.array([[0.0]]),
            actual_units=np.array([[900]], dtype=np.int64),
        )
        with self.assertRaises(ValueError):
            simulation_to_records(result, self.factory)

    def test_bridge_invalid_inputs_section_7_5(self) -> None:
        result = build_fixed_result()
        with self.assertRaises(TypeError):
            simulation_to_records(result, ["not", "a", "dict"])
        with self.assertRaises(TypeError):
            simulation_to_records("not a result", self.factory)

        # Multi-shift machine where planned_units = 1 -> second shift gets 0 -> ValueError
        config = SimulationConfig(
            machine_ids=["M2"],
            working_hours=[16.0],
            cycle_time_sec=[45.0],
            base_efficiency_pct=[90.0],
            efficiency_min_pct=[80.0],
            efficiency_max_pct=[95.0],
            days=1,
        )
        low_plan_result = SimulationResult(
            config=config,
            theoretical_capacity=np.array([1280.0]),
            efficiency_pct=np.array([[90.0]]),
            effective_capacity=np.array([[1152.0]]),
            planned_units=np.array([[1]], dtype=np.int64),
            downtime_hours=np.array([[0.0]]),
            actual_units=np.array([[1]], dtype=np.int64),
        )
        with self.assertRaises(ValueError):
            simulation_to_records(low_plan_result, self.factory)


class TestBenchmarkScenario13(unittest.TestCase):
    """Section 7.4 scenario 13: loop vs. NumPy benchmark."""

    def test_compare_loop_and_numpy_small_and_report(self) -> None:
        bench = compare_loop_and_numpy(machine_count=50, days=30)
        self.assertTrue(bench["results_match"])
        self.assertEqual(bench["cell_count"], 1500)
        self.assertGreater(bench["loop_seconds"], 0.0)
        self.assertGreater(bench["numpy_seconds"], 0.0)
        report = build_benchmark_report(bench)
        self.assertIn("DÖNGÜ / NUMPY HIZ KARŞILAŞTIRMASI", report)
        self.assertIn("Evet (np.allclose)", report)

    def test_invalid_benchmark_inputs(self) -> None:
        with self.assertRaises(TypeError):
            compare_loop_and_numpy(machine_count="100", days=10)
        with self.assertRaises(ValueError):
            compare_loop_and_numpy(machine_count=0, days=10)


if __name__ == "__main__":
    unittest.main()
