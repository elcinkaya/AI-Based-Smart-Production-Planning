"""
test_stats.py - Unit tests for stats.py and report.py.

Uses the hand-verified fixed 2x3 example of Section 7.2 (no randomness):
calculate_statistics (ddof=0, all cells / axis=1 / axis=0), the summary
dictionary of Section 3.5, summarize_by_machine and the exact report text.

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

import numpy as np

from capacity_simulation.models import SimulationConfig, SimulationResult
from capacity_simulation.report import build_simulation_report, print_simulation_report
from capacity_simulation.stats import (
    SIMULATION_SUMMARY_KEYS,
    calculate_statistics,
    summarize_by_machine,
    summarize_simulation,
)


def build_fixed_result(actual_units: np.ndarray | None = None) -> SimulationResult:
    """Return the Section 7.2 fixed 2x3 SimulationResult (M1 8 h/30 s, M2 16 h/45 s)."""
    config = SimulationConfig(
        machine_ids=["M1", "M2"],
        working_hours=[8.0, 16.0],
        cycle_time_sec=[30.0, 45.0],
        base_efficiency_pct=[85.0, 90.0],
        efficiency_min_pct=[75.0, 80.0],
        efficiency_max_pct=[90.0, 100.0],
        days=3,
    )
    planned = np.array([[816, 768, 432], [576, 1216, 1280]], dtype=np.int64)
    actual = np.array([[816, 691, 324], [558, 1216, 1280]], dtype=np.int64)
    return SimulationResult(
        config=config,
        theoretical_capacity=np.array([960.0, 1280.0]),
        efficiency_pct=np.array([[85.0, 80.0, 90.0], [90.0, 95.0, 100.0]]),
        effective_capacity=np.array([[816.0, 768.0, 864.0], [1152.0, 1216.0, 1280.0]]),
        planned_units=planned,
        downtime_hours=np.array([[0.0, 0.0, 2.0], [0.5, 0.0, 0.0]]),
        actual_units=actual if actual_units is None else actual_units,
    )


EXPECTED_REPORT = """\
==============================================
  KAPASİTE VE VERİMLİLİK SİMÜLASYON RAPORU
==============================================
Kapsam
  Makine sayısı         : 2
  Gün sayısı            : 3
  Tarih aralığı         : 2026-10-01 – 2026-10-03
----------------------------------------------
Genel Sonuçlar
  Planlanan üretim      : 5088 adet
  Gerçekleşen üretim    : 4885 adet
  Üretim farkı          : -203 adet
  Plan gerçekleşme      : %96.01
  Toplam duruş          : 2.50 saat
  Kullanılabilirlik     : %96.53
----------------------------------------------
İstatistikler (tüm makine-günler)
                           Ortalama      Std      Min      Maks
  Verimlilik (%)              90.00     6.45    80.00    100.00
  Efektif kapasite (adet)   1016.00   205.26   768.00   1280.00
  Gerçekleşen üretim (adet)  814.17   341.45   324.00   1280.00
----------------------------------------------
Makine Bazında
  M1 : planlanan 2016, gerçekleşen 1831, fark -185, %90.82
  M2 : planlanan 3072, gerçekleşen 3054, fark -18, %99.41
----------------------------------------------
DURUM: PLAN KARŞILANMADI
Üretim açığı: 203 adet
=============================================="""


class TestCalculateStatistics(unittest.TestCase):
    """calculate_statistics on the Section 7.2 arrays (ddof=0)."""

    def setUp(self) -> None:
        self.result = build_fixed_result()

    def test_all_cells(self) -> None:
        expected = {
            "efficiency_pct": (90.00, 6.45, 80, 100),
            "effective_capacity": (1016.00, 205.26, 768, 1280),
            "actual_units": (814.17, 341.45, 324, 1280),
        }
        for field, (mean, std, low, high) in expected.items():
            with self.subTest(field=field):
                stats = calculate_statistics(getattr(self.result, field))
                self.assertAlmostEqual(stats["mean"], mean, delta=0.01)
                self.assertAlmostEqual(stats["std"], std, delta=0.01)
                self.assertAlmostEqual(stats["min"], low, delta=0.01)
                self.assertAlmostEqual(stats["max"], high, delta=0.01)

    def test_all_cells_returns_python_floats(self) -> None:
        stats = calculate_statistics(self.result.actual_units)
        self.assertEqual(list(stats), ["mean", "std", "min", "max"])
        for value in stats.values():
            self.assertIs(type(value), float)

    def test_axis_1_per_machine(self) -> None:
        stats = calculate_statistics(self.result.effective_capacity, axis=1)
        self.assertTrue(np.allclose(stats["mean"], [816.00, 1216.00]))
        self.assertTrue(np.allclose(stats["std"], [39.19, 52.26], atol=0.01))
        self.assertTrue(np.allclose(stats["min"], [768, 1152]))
        self.assertTrue(np.allclose(stats["max"], [864, 1280]))
        self.assertIsInstance(stats["mean"], list)

    def test_axis_0_per_day(self) -> None:
        stats = calculate_statistics(self.result.effective_capacity, axis=0)
        self.assertTrue(np.allclose(stats["mean"], [984, 992, 1072]))
        self.assertEqual(len(stats["std"]), 3)

    def test_ddof_zero_not_one(self) -> None:
        # With ddof=1 the M1 std would be 48.0 (Section 7.2).
        m1_std = calculate_statistics(self.result.effective_capacity, axis=1)["std"][0]
        self.assertAlmostEqual(m1_std, 39.19, delta=0.01)
        self.assertNotAlmostEqual(m1_std, 48.0, delta=0.01)

    def test_input_not_modified(self) -> None:
        values = self.result.effective_capacity.copy()
        calculate_statistics(values, axis=1)
        self.assertTrue(np.array_equal(values, self.result.effective_capacity))

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(TypeError):
            calculate_statistics([1.0, 2.0])
        with self.assertRaises(ValueError):
            calculate_statistics(np.array([]))
        with self.assertRaises(ValueError):
            calculate_statistics(np.array(["a", "b"]))
        with self.assertRaises(ValueError):
            calculate_statistics(np.array([1.0, np.nan]))
        with self.assertRaises(ValueError):
            calculate_statistics(np.ones((2, 3)), axis=2)
        with self.assertRaises(TypeError):
            calculate_statistics(np.ones((2, 3)), axis=1.0)


class TestSummarizeSimulation(unittest.TestCase):
    """Section 3.5 summary dictionary for the fixed example."""

    def setUp(self) -> None:
        self.summary = summarize_simulation(build_fixed_result())

    def test_keys_in_contract_order(self) -> None:
        self.assertEqual(tuple(self.summary), SIMULATION_SUMMARY_KEYS)

    def test_values(self) -> None:
        s = self.summary
        self.assertEqual(s["machine_count"], 2)
        self.assertEqual(s["day_count"], 3)
        self.assertEqual(s["date_from"], "2026-10-01")
        self.assertEqual(s["date_to"], "2026-10-03")
        self.assertEqual(s["total_planned_units"], 5088)
        self.assertEqual(s["total_actual_units"], 4885)
        self.assertEqual(s["production_gap"], -203)
        self.assertAlmostEqual(s["attainment_pct"], 96.01, delta=0.01)
        self.assertAlmostEqual(s["total_downtime_hours"], 2.5, delta=0.01)
        self.assertAlmostEqual(s["availability_pct"], 96.53, delta=0.01)
        self.assertFalse(s["plan_met"])
        self.assertEqual(s["status_message"], "Plan karşılanmadı. Üretim açığı: 203 adet.")

    def test_python_types(self) -> None:
        s = self.summary
        for key in ("machine_count", "day_count", "total_planned_units",
                    "total_actual_units", "production_gap"):
            self.assertIs(type(s[key]), int, key)
        for key in ("attainment_pct", "total_downtime_hours", "availability_pct"):
            self.assertIs(type(s[key]), float, key)
        self.assertIs(type(s["plan_met"]), bool)

    def test_not_rounded(self) -> None:
        self.assertEqual(self.summary["attainment_pct"], 4885 / 5088 * 100)
        self.assertEqual(self.summary["availability_pct"], (72 - 2.5) / 72 * 100)

    def test_statistics_block(self) -> None:
        stats = self.summary["statistics"]
        self.assertEqual(list(stats), ["efficiency_pct", "effective_capacity", "actual_units"])
        self.assertAlmostEqual(stats["effective_capacity"]["std"], 205.26, delta=0.01)
        self.assertAlmostEqual(stats["actual_units"]["mean"], 814.17, delta=0.01)

    def test_status_messages_match_mp3(self) -> None:
        planned = np.array([[816, 768, 432], [576, 1216, 1280]], dtype=np.int64)
        exact = summarize_simulation(build_fixed_result(planned.copy()))
        self.assertTrue(exact["plan_met"])
        self.assertEqual(exact["status_message"], "Plan tam olarak gerçekleşti.")
        surplus = planned.copy()
        surplus[0, 0] += 7
        over = summarize_simulation(build_fixed_result(surplus))
        self.assertTrue(over["plan_met"])
        self.assertEqual(over["status_message"], "Plan karşılandı. Fazla üretim: 7 adet.")

    def test_type_error(self) -> None:
        with self.assertRaises(TypeError):
            summarize_simulation({"planned_units": [1]})


class TestSummarizeByMachine(unittest.TestCase):
    """Per-machine table of Section 7.2."""

    def test_values(self) -> None:
        machines = summarize_by_machine(build_fixed_result())
        self.assertEqual(list(machines), ["M1", "M2"])
        expected = {
            "M1": (2016, 1831, -185, 90.82, 2.0, 91.67),
            "M2": (3072, 3054, -18, 99.41, 0.5, 98.96),
        }
        for machine_id, (planned, actual, gap, att, down, avail) in expected.items():
            with self.subTest(machine=machine_id):
                s = machines[machine_id]
                self.assertEqual(tuple(s), SIMULATION_SUMMARY_KEYS)
                self.assertEqual(s["machine_count"], 1)
                self.assertEqual(s["total_planned_units"], planned)
                self.assertEqual(s["total_actual_units"], actual)
                self.assertEqual(s["production_gap"], gap)
                self.assertAlmostEqual(s["attainment_pct"], att, delta=0.01)
                self.assertAlmostEqual(s["total_downtime_hours"], down, delta=0.01)
                self.assertAlmostEqual(s["availability_pct"], avail, delta=0.01)
                self.assertFalse(s["plan_met"])

    def test_machine_statistics_match_axis_1(self) -> None:
        machines = summarize_by_machine(build_fixed_result())
        self.assertAlmostEqual(machines["M1"]["statistics"]["effective_capacity"]["mean"], 816.0)
        self.assertAlmostEqual(machines["M2"]["statistics"]["effective_capacity"]["std"], 52.26, delta=0.01)

    def test_type_error(self) -> None:
        with self.assertRaises(TypeError):
            summarize_by_machine(None)


class TestReport(unittest.TestCase):
    """build_simulation_report / print_simulation_report."""

    def setUp(self) -> None:
        result = build_fixed_result()
        self.summary = summarize_simulation(result)
        self.machines = summarize_by_machine(result)

    def test_exact_report_text(self) -> None:
        self.assertEqual(build_simulation_report(self.summary, self.machines), EXPECTED_REPORT)

    def test_without_machine_section(self) -> None:
        text = build_simulation_report(self.summary)
        self.assertNotIn("Makine Bazında", text)
        self.assertIn("DURUM: PLAN KARŞILANMADI", text)

    def test_surplus_status(self) -> None:
        surplus = dict(self.summary, production_gap=12, plan_met=True)
        text = build_simulation_report(surplus)
        self.assertIn("DURUM: PLAN KARŞILANDI\nFazla üretim: 12 adet", text)

    def test_print_writes_same_text(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_simulation_report(self.summary, self.machines)
        self.assertEqual(buffer.getvalue(), EXPECTED_REPORT + "\n")

    def test_build_does_not_print(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            build_simulation_report(self.summary)
        self.assertEqual(buffer.getvalue(), "")

    def test_invalid_summary(self) -> None:
        with self.assertRaises(TypeError):
            build_simulation_report([1, 2])
        broken = dict(self.summary)
        del broken["availability_pct"]
        with self.assertRaises(ValueError):
            build_simulation_report(broken)
        with self.assertRaises(TypeError):
            build_simulation_report(self.summary, ["M1"])


if __name__ == "__main__":
    unittest.main()
