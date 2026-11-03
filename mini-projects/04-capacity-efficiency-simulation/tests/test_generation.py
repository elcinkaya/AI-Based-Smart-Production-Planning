"""
test_generation.py – Unit tests for the random matrices and production formulas.

Covers (Section 5, Kişi B; Section 7.2; Section 7.5):
- shapes and dtypes of every random matrix,
- value ranges (efficiency per machine, load, performance, downtime),
- same seed -> same arrays, different seed -> different arrays,
- downtime is 0 or a multiple of 0.25 and <= working_hours,
- deterministic formulas with the fixed 2x3 example of Section 7.2,
- invalid inputs and "input arrays are not modified".

Author: Kişi B
Mini Project: 04 – Capacity and Efficiency Simulation
"""
from __future__ import annotations

import unittest

import numpy as np

from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from capacity_simulation.generation import (
    calculate_actual_units,
    calculate_planned_units,
    create_rng,
    generate_downtime_matrix,
    generate_efficiency_matrix,
    generate_load_factor_matrix,
    generate_performance_factor_matrix,
)

# Golden configuration ranges (Section 7.3) used for property tests
EFF_MIN = np.array([75.0, 80.0, 60.0, 70.0])
EFF_MAX = np.array([90.0, 95.0, 75.0, 85.0])
WORKING_HOURS = np.array([8.0, 16.0, 8.0, 8.0])
SHAPE = (4, 30)

# Fixed 2x3 example (Section 7.2): M1 (8 h, 30 s), M2 (16 h, 45 s)
FIXED_WORKING_HOURS = np.array([8.0, 16.0])
FIXED_CYCLE_TIME_SEC = np.array([30.0, 45.0])
FIXED_EFFICIENCY = np.array([[85.0, 80.0, 90.0], [90.0, 95.0, 100.0]])
FIXED_LOAD = np.array([[1.0, 1.0, 0.5], [0.5, 1.0, 1.0]])
FIXED_PERFORMANCE = np.array([[1.0, 0.9, 1.0], [1.0, 1.0, 1.0]])
FIXED_DOWNTIME = np.array([[0.0, 0.0, 2.0], [0.5, 0.0, 0.0]])
EXPECTED_THEORETICAL = np.array([960.0, 1280.0])
EXPECTED_EFFECTIVE = np.array([[816.0, 768.0, 864.0], [1152.0, 1216.0, 1280.0]])
EXPECTED_PLANNED = np.array([[816, 768, 432], [576, 1216, 1280]], dtype=np.int64)
EXPECTED_ACTUAL = np.array([[816, 691, 324], [558, 1216, 1280]], dtype=np.int64)


def _all_random_matrices(seed: int) -> dict:
    """Generate all five matrices in the Section 3.3 order with one rng."""
    rng = create_rng(seed)
    return {
        "efficiency": generate_efficiency_matrix(rng, EFF_MIN, EFF_MAX, SHAPE[1]),
        "load": generate_load_factor_matrix(rng, SHAPE),
        "downtime": generate_downtime_matrix(rng, SHAPE, WORKING_HOURS),
        "performance": generate_performance_factor_matrix(rng, SHAPE),
    }


class TestCreateRng(unittest.TestCase):
    """create_rng returns a seeded default_rng Generator."""

    def test_returns_generator(self):
        self.assertIsInstance(create_rng(42), np.random.Generator)

    def test_same_stream_as_default_rng(self):
        self.assertTrue(np.array_equal(
            create_rng(42).random(5), np.random.default_rng(42).random(5)))

    def test_negative_seed_raises(self):
        with self.assertRaises(ValueError):
            create_rng(-1)

    def test_wrong_type_raises(self):
        for bad in ("42", 4.2, True, None):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                create_rng(bad)


class TestShapesAndRanges(unittest.TestCase):
    """Shapes, dtypes and ranges of the random matrices."""

    @classmethod
    def setUpClass(cls):
        cls.m = _all_random_matrices(42)

    def test_shapes_and_dtypes(self):
        for name, matrix in self.m.items():
            with self.subTest(name=name):
                self.assertEqual(matrix.shape, SHAPE)
                self.assertEqual(matrix.dtype, np.float64)

    def test_efficiency_in_machine_range(self):
        eff = self.m["efficiency"]
        self.assertTrue(np.all(eff >= EFF_MIN[:, None]))
        self.assertTrue(np.all(eff <= EFF_MAX[:, None]))

    def test_load_factor_range(self):
        load = self.m["load"]
        self.assertTrue(np.all((load >= 0.80) & (load <= 1.00)))

    def test_performance_factor_range(self):
        perf = self.m["performance"]
        self.assertTrue(np.all((perf >= 0.90) & (perf <= 1.05)))

    def test_downtime_quarter_hours_and_capped(self):
        down = self.m["downtime"]
        self.assertTrue(np.array_equal(down * 4, np.rint(down * 4)))
        self.assertTrue(np.all(down >= 0))
        self.assertTrue(np.all(down <= WORKING_HOURS[:, None]))
        positive = down[down > 0]
        self.assertTrue(np.all((positive >= 0.25) & (positive <= 3.0)))

    def test_downtime_has_both_zero_and_positive(self):
        down = self.m["downtime"]
        self.assertTrue(np.any(down == 0))
        self.assertTrue(np.any(down > 0))

    def test_downtime_capped_by_short_working_hours(self):
        hours = np.array([0.5, 1.0])
        down = generate_downtime_matrix(create_rng(1), (2, 500), hours)
        self.assertTrue(np.all(down <= hours[:, None]))
        self.assertEqual(down[0].max(), 0.5)
        self.assertTrue(np.array_equal(down * 4, np.rint(down * 4)))

    def test_efficiency_equal_bounds(self):
        bounds = np.array([80.0, 100.0])
        eff = generate_efficiency_matrix(create_rng(0), bounds, bounds, 5)
        self.assertTrue(np.allclose(eff, bounds[:, None]))


class TestReproducibility(unittest.TestCase):
    """Same seed -> same arrays; different seed -> different arrays."""

    def test_same_seed_same_arrays(self):
        first, second = _all_random_matrices(42), _all_random_matrices(42)
        for name in first:
            with self.subTest(name=name):
                self.assertTrue(np.array_equal(first[name], second[name]))

    def test_different_seed_different_arrays(self):
        first, second = _all_random_matrices(42), _all_random_matrices(43)
        for name in ("efficiency", "load", "performance"):
            with self.subTest(name=name):
                self.assertFalse(np.array_equal(first[name], second[name]))

    def test_draw_order_section_3_3(self):
        """Each function consumes exactly the Section 3.3 draws in order."""
        rng = np.random.default_rng(7)
        ref_eff = rng.uniform(EFF_MIN[:, None], EFF_MAX[:, None], size=SHAPE)
        ref_load = rng.uniform(0.80, 1.00, size=SHAPE)
        ref_occ = rng.random(SHAPE)
        ref_amount = rng.uniform(0.25, 3.0, size=SHAPE)
        ref_perf = rng.uniform(0.90, 1.05, size=SHAPE)
        ref_down = np.minimum(
            np.where(ref_occ < 0.30, np.round(ref_amount * 4) / 4, 0.0),
            WORKING_HOURS[:, None],
        )

        m = _all_random_matrices(7)
        self.assertTrue(np.array_equal(m["efficiency"], ref_eff))
        self.assertTrue(np.array_equal(m["load"], ref_load))
        self.assertTrue(np.array_equal(m["downtime"], ref_down))
        self.assertTrue(np.array_equal(m["performance"], ref_perf))

    def test_global_random_state_not_used(self):
        state = np.random.get_state()[1].copy()
        _all_random_matrices(42)
        self.assertTrue(np.array_equal(state, np.random.get_state()[1]))


class TestFixedExample(unittest.TestCase):
    """Deterministic formulas with the hand-checked 2x3 example (Section 7.2)."""

    def test_theoretical_and_effective_capacity(self):
        theoretical = calculate_theoretical_capacity_array(FIXED_WORKING_HOURS, FIXED_CYCLE_TIME_SEC)
        effective = calculate_effective_capacity_array(theoretical, FIXED_EFFICIENCY)
        self.assertTrue(np.allclose(theoretical, EXPECTED_THEORETICAL))
        self.assertTrue(np.allclose(effective, EXPECTED_EFFECTIVE))

    def test_planned_units(self):
        planned = calculate_planned_units(EXPECTED_EFFECTIVE, FIXED_LOAD)
        self.assertEqual(planned.dtype, np.int64)
        self.assertTrue(np.array_equal(planned, EXPECTED_PLANNED))

    def test_actual_units(self):
        actual = calculate_actual_units(
            EXPECTED_PLANNED, FIXED_PERFORMANCE, FIXED_DOWNTIME, FIXED_WORKING_HOURS)
        self.assertEqual(actual.dtype, np.int64)
        self.assertTrue(np.array_equal(actual, EXPECTED_ACTUAL))

    def test_hand_calculation_notes(self):
        actual = calculate_actual_units(
            EXPECTED_PLANNED, FIXED_PERFORMANCE, FIXED_DOWNTIME, FIXED_WORKING_HOURS)
        self.assertEqual(actual[0, 1], 691)   # 768 * 0.9 = 691.2 -> 691
        self.assertEqual(actual[0, 2], 324)   # 432 * (1 - 2/8) = 324
        self.assertEqual(actual[1, 0], 558)   # 576 * (1 - 0.5/16) = 558

    def test_totals(self):
        actual = calculate_actual_units(
            EXPECTED_PLANNED, FIXED_PERFORMANCE, FIXED_DOWNTIME, FIXED_WORKING_HOURS)
        self.assertEqual(int(EXPECTED_PLANNED.sum()), 5088)
        self.assertEqual(int(actual.sum()), 4885)
        self.assertAlmostEqual(float(FIXED_DOWNTIME.sum()), 2.5, delta=0.01)

    def test_rint_rounds_half_to_even(self):
        capacity = np.array([[2.5, 3.5, 1.5]])
        planned = calculate_planned_units(capacity, np.ones((1, 3)))
        self.assertTrue(np.array_equal(planned, [[2, 4, 2]]))

    def test_full_downtime_gives_zero_actual(self):
        actual = calculate_actual_units(
            np.array([[100, 100]]), np.array([[1.05, 1.0]]),
            np.array([[8.0, 0.0]]), np.array([8.0]))
        self.assertTrue(np.array_equal(actual, [[0, 100]]))

    def test_inputs_not_modified(self):
        arrays = [EXPECTED_EFFECTIVE, FIXED_LOAD, EXPECTED_PLANNED,
                  FIXED_PERFORMANCE, FIXED_DOWNTIME, FIXED_WORKING_HOURS]
        copies = [a.copy() for a in arrays]
        calculate_planned_units(EXPECTED_EFFECTIVE, FIXED_LOAD)
        calculate_actual_units(EXPECTED_PLANNED, FIXED_PERFORMANCE, FIXED_DOWNTIME, FIXED_WORKING_HOURS)
        for original, copy in zip(arrays, copies):
            self.assertTrue(np.array_equal(original, copy))

    def test_generators_do_not_modify_inputs(self):
        low, high, hours = EFF_MIN.copy(), EFF_MAX.copy(), WORKING_HOURS.copy()
        _all_random_matrices(42)
        self.assertTrue(np.array_equal(low, EFF_MIN))
        self.assertTrue(np.array_equal(high, EFF_MAX))
        self.assertTrue(np.array_equal(hours, WORKING_HOURS))


class TestInvalidInputs(unittest.TestCase):
    """Invalid inputs raise ValueError / TypeError (Section 7.5)."""

    def test_planned_below_one_raises(self):
        # Very large cycle time -> effective capacity well below 1 unit/day.
        theoretical = calculate_theoretical_capacity_array(np.array([8.0]), np.array([100000.0]))
        effective = calculate_effective_capacity_array(theoretical, np.array([[80.0, 80.0]]))
        with self.assertRaises(ValueError):
            calculate_planned_units(effective, np.full((1, 2), 0.8))

    def test_planned_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            calculate_planned_units(EXPECTED_EFFECTIVE, np.ones((2, 2)))

    def test_actual_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            calculate_actual_units(EXPECTED_PLANNED, FIXED_PERFORMANCE,
                                   FIXED_DOWNTIME, np.array([8.0, 16.0, 8.0]))
        with self.assertRaises(ValueError):
            calculate_actual_units(EXPECTED_PLANNED, np.ones((2, 2)),
                                   FIXED_DOWNTIME, FIXED_WORKING_HOURS)

    def test_actual_downtime_above_working_hours_raises(self):
        with self.assertRaises(ValueError):
            calculate_actual_units(EXPECTED_PLANNED, FIXED_PERFORMANCE,
                                   np.full((2, 3), 9.0), np.array([8.0, 8.0]))

    def test_text_array_raises(self):
        with self.assertRaises(ValueError):
            calculate_planned_units(np.array([["a", "b"]]), np.ones((1, 2)))

    def test_efficiency_bad_ranges_raise(self):
        rng = create_rng(0)
        with self.assertRaises(ValueError):
            generate_efficiency_matrix(rng, np.array([90.0]), np.array([80.0]), 3)
        with self.assertRaises(ValueError):
            generate_efficiency_matrix(rng, np.array([0.0]), np.array([80.0]), 3)
        with self.assertRaises(ValueError):
            generate_efficiency_matrix(rng, np.array([90.0]), np.array([120.0]), 3)
        with self.assertRaises(ValueError):
            generate_efficiency_matrix(rng, np.array([70.0, 80.0]), np.array([90.0]), 3)
        with self.assertRaises(ValueError):
            generate_efficiency_matrix(rng, np.array([70.0]), np.array([90.0]), 0)

    def test_downtime_working_hours_mismatch_raises(self):
        with self.assertRaises(ValueError):
            generate_downtime_matrix(create_rng(0), (2, 3), np.array([8.0]))
        with self.assertRaises(ValueError):
            generate_downtime_matrix(create_rng(0), (1, 3), np.array([25.0]))

    def test_bad_shape_and_rng_raise(self):
        with self.assertRaises(TypeError):
            generate_load_factor_matrix(create_rng(0), [2, 3])
        with self.assertRaises(ValueError):
            generate_performance_factor_matrix(create_rng(0), (0, 3))
        with self.assertRaises(TypeError):
            generate_load_factor_matrix(42, (2, 3))


if __name__ == "__main__":
    unittest.main()
