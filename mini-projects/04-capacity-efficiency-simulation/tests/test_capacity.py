"""
test_capacity.py – Unit tests for the vectorized capacity functions.

Covers the MP1 compatibility scenarios (Section 7.1): vectorized results
must equal the MP1 scalar functions run in a reference loop
(np.allclose), plus invalid input tests (Section 7.5).  Loops appear here
only as the reference implementation.

Author: Kişi A
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from factory_model import calculations as mp1

SIMULATION_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "simulation_config.json"

# Section 7.1 – MP1 scenarios as one array
WORKING_HOURS = np.array([8.0, 16.0, 8.0, 10.0, 8.0])
CYCLE_TIME_SEC = np.array([30.0, 45.0, 60.0, 20.0, 30.0])
EFFICIENCY_PCT = np.array([[85.0], [90.0], [70.0], [95.0], [80.0]])
EXPECTED_THEORETICAL = np.array([960.0, 1280.0, 480.0, 1800.0, 960.0])
EXPECTED_EFFECTIVE = np.array([[816.0], [1152.0], [336.0], [1710.0], [768.0]])


def _reference_theoretical(working_hours: np.ndarray, cycle_time_sec: np.ndarray) -> np.ndarray:
    """Reference implementation: MP1 scalar function in a Python loop."""
    return np.array([
        mp1.theoretical_capacity(float(h), float(c))
        for h, c in zip(working_hours, cycle_time_sec)
    ])


def _reference_effective(theoretical: np.ndarray, efficiency_pct: np.ndarray) -> np.ndarray:
    """Reference implementation: MP1 scalar function in nested Python loops."""
    rows, cols = efficiency_pct.shape
    result = np.empty((rows, cols))
    for i in range(rows):
        for j in range(cols):
            result[i, j] = mp1.effective_capacity(float(theoretical[i]), float(efficiency_pct[i, j]))
    return result


class TestTheoreticalCapacityArray(unittest.TestCase):
    """calculate_theoretical_capacity_array – values and MP1 compatibility."""

    def test_section_7_1_values(self) -> None:
        result = calculate_theoretical_capacity_array(WORKING_HOURS, CYCLE_TIME_SEC)
        self.assertEqual(result.shape, (5,))
        self.assertEqual(result.dtype, np.float64)
        self.assertTrue(np.allclose(result, EXPECTED_THEORETICAL))

    def test_matches_mp1_loop(self) -> None:
        result = calculate_theoretical_capacity_array(WORKING_HOURS, CYCLE_TIME_SEC)
        self.assertTrue(np.allclose(result, _reference_theoretical(WORKING_HOURS, CYCLE_TIME_SEC)))

    def test_matches_mp1_loop_random_machines(self) -> None:
        rng = np.random.default_rng(2026)
        hours = rng.uniform(0.5, 24.0, size=200)
        cycles = rng.uniform(1.0, 120.0, size=200)
        result = calculate_theoretical_capacity_array(hours, cycles)
        self.assertTrue(np.allclose(result, _reference_theoretical(hours, cycles)))

    def test_sample_factory_config(self) -> None:
        with open(SIMULATION_CONFIG_PATH, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        result = calculate_theoretical_capacity_array(
            np.array(config["working_hours"]), np.array(config["cycle_time_sec"])
        )
        self.assertTrue(np.allclose(result, [960.0, 1280.0, 480.0, 960.0]))

    def test_integer_and_list_input(self) -> None:
        result = calculate_theoretical_capacity_array(np.array([8, 16]), [30, 45])
        self.assertEqual(result.dtype, np.float64)
        self.assertTrue(np.allclose(result, [960.0, 1280.0]))

    def test_boundary_24_hours(self) -> None:
        result = calculate_theoretical_capacity_array(np.array([24.0]), np.array([60.0]))
        self.assertTrue(np.allclose(result, [1440.0]))

    def test_inputs_are_not_modified(self) -> None:
        hours = WORKING_HOURS.copy()
        cycles = CYCLE_TIME_SEC.copy()
        result = calculate_theoretical_capacity_array(hours, cycles)
        self.assertTrue(np.array_equal(hours, WORKING_HOURS))
        self.assertTrue(np.array_equal(cycles, CYCLE_TIME_SEC))
        self.assertFalse(np.shares_memory(result, hours))

    # -- invalid input ------------------------------------------------------

    def test_shape_mismatch(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            calculate_theoretical_capacity_array(WORKING_HOURS, np.append(CYCLE_TIME_SEC, 30.0))
        self.assertIn("şekilleri aynı", str(ctx.exception))

    def test_wrong_dimension(self) -> None:
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(WORKING_HOURS[:, None], CYCLE_TIME_SEC[:, None])
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(np.array(8.0), np.array(30.0))

    def test_empty_array(self) -> None:
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(np.array([]), np.array([]))

    def test_cycle_time_not_positive(self) -> None:
        for bad in (0.0, -5.0):
            with self.subTest(cycle_time_sec=bad):
                with self.assertRaises(ValueError) as ctx:
                    calculate_theoretical_capacity_array(np.array([8.0, 8.0]), np.array([30.0, bad]))
                self.assertIn("Çevrim süresi", str(ctx.exception))

    def test_working_hours_out_of_range(self) -> None:
        for bad in (0.0, -1.0, 25.0):
            with self.subTest(working_hours=bad):
                with self.assertRaises(ValueError) as ctx:
                    calculate_theoretical_capacity_array(np.array([bad, 8.0]), np.array([30.0, 30.0]))
                self.assertIn("çalışma süresi", str(ctx.exception))

    def test_text_in_array(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            calculate_theoretical_capacity_array(np.array([8, "sekiz"]), np.array([30.0, 30.0]))
        self.assertIn("sayısal", str(ctx.exception))
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(np.array([8.0, 8.0]), ["30", "30"])

    def test_bool_and_nan_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(np.array([True, True]), np.array([30.0, 30.0]))
        with self.assertRaises(ValueError):
            calculate_theoretical_capacity_array(np.array([8.0, np.nan]), np.array([30.0, 30.0]))


class TestEffectiveCapacityArray(unittest.TestCase):
    """calculate_effective_capacity_array – broadcasting and MP1 compatibility."""

    def test_section_7_1_values(self) -> None:
        result = calculate_effective_capacity_array(EXPECTED_THEORETICAL, EFFICIENCY_PCT)
        self.assertEqual(result.shape, (5, 1))
        self.assertEqual(result.dtype, np.float64)
        self.assertTrue(np.allclose(result, EXPECTED_EFFECTIVE))

    def test_section_7_1_pipeline_matches_mp1_loop(self) -> None:
        theoretical = calculate_theoretical_capacity_array(WORKING_HOURS, CYCLE_TIME_SEC)
        result = calculate_effective_capacity_array(theoretical, EFFICIENCY_PCT)
        reference = _reference_effective(
            _reference_theoretical(WORKING_HOURS, CYCLE_TIME_SEC), EFFICIENCY_PCT
        )
        self.assertTrue(np.allclose(result, reference))
        self.assertTrue(np.allclose(result, EXPECTED_EFFECTIVE))

    def test_fixed_2x3_sample(self) -> None:
        # Section 7.2: M1 (8 h, 30 s), M2 (16 h, 45 s), 3 days
        theoretical = calculate_theoretical_capacity_array(np.array([8.0, 16.0]), np.array([30.0, 45.0]))
        efficiency = np.array([[85.0, 80.0, 90.0], [90.0, 95.0, 100.0]])
        result = calculate_effective_capacity_array(theoretical, efficiency)
        self.assertEqual(result.shape, (2, 3))
        self.assertTrue(np.allclose(result, [[816.0, 768.0, 864.0], [1152.0, 1216.0, 1280.0]]))

    def test_matches_mp1_loop_random_matrix(self) -> None:
        rng = np.random.default_rng(42)
        theoretical = rng.uniform(100.0, 2000.0, size=5)
        efficiency = rng.uniform(1.0, 100.0, size=(5, 30))
        result = calculate_effective_capacity_array(theoretical, efficiency)
        self.assertEqual(result.shape, (5, 30))
        self.assertTrue(np.allclose(result, _reference_effective(theoretical, efficiency)))

    def test_broadcasting_per_machine_row(self) -> None:
        theoretical = np.array([1000.0, 2000.0])
        efficiency = np.full((2, 4), 50.0)
        result = calculate_effective_capacity_array(theoretical, efficiency)
        self.assertTrue(np.allclose(result[0], 500.0))
        self.assertTrue(np.allclose(result[1], 1000.0))

    def test_boundary_100_pct(self) -> None:
        result = calculate_effective_capacity_array(np.array([960.0]), np.array([[100.0]]))
        self.assertTrue(np.allclose(result, [[960.0]]))

    def test_inputs_are_not_modified(self) -> None:
        theoretical = EXPECTED_THEORETICAL.copy()
        efficiency = EFFICIENCY_PCT.copy()
        calculate_effective_capacity_array(theoretical, efficiency)
        self.assertTrue(np.array_equal(theoretical, EXPECTED_THEORETICAL))
        self.assertTrue(np.array_equal(efficiency, EFFICIENCY_PCT))

    # -- invalid input ------------------------------------------------------

    def test_shape_mismatch(self) -> None:
        # (M+1,) theoretical capacity for an (M, D) efficiency matrix
        with self.assertRaises(ValueError) as ctx:
            calculate_effective_capacity_array(np.append(EXPECTED_THEORETICAL, 960.0), EFFICIENCY_PCT)
        self.assertIn("aynı olmalıdır", str(ctx.exception))
        with self.assertRaises(ValueError):
            calculate_effective_capacity_array(EXPECTED_THEORETICAL, np.ones((6, 3)) * 80.0)

    def test_wrong_dimension(self) -> None:
        with self.assertRaises(ValueError):
            calculate_effective_capacity_array(EXPECTED_THEORETICAL, EFFICIENCY_PCT.ravel())
        with self.assertRaises(ValueError):
            calculate_effective_capacity_array(EXPECTED_THEORETICAL[:, None], EFFICIENCY_PCT)

    def test_efficiency_out_of_range(self) -> None:
        for bad in (0.0, -10.0, 120.0):
            with self.subTest(efficiency_pct=bad):
                efficiency = EFFICIENCY_PCT.copy()
                efficiency[2, 0] = bad
                with self.assertRaises(ValueError) as ctx:
                    calculate_effective_capacity_array(EXPECTED_THEORETICAL, efficiency)
                self.assertIn("Verimlilik", str(ctx.exception))

    def test_negative_theoretical_capacity(self) -> None:
        theoretical = EXPECTED_THEORETICAL.copy()
        theoretical[0] = -1.0
        with self.assertRaises(ValueError) as ctx:
            calculate_effective_capacity_array(theoretical, EFFICIENCY_PCT)
        self.assertIn("negatif", str(ctx.exception))

    def test_text_in_array(self) -> None:
        with self.assertRaises(ValueError):
            calculate_effective_capacity_array(EXPECTED_THEORETICAL, np.array([["85"], ["90"], ["70"], ["95"], ["80"]]))
        with self.assertRaises(ValueError):
            calculate_effective_capacity_array(np.array(["960"] * 5), EFFICIENCY_PCT)


if __name__ == "__main__":
    unittest.main()
