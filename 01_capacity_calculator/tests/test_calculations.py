"""
test_calculations.py – Unit Tests for calculations.py

Tests all calculation functions against the 7 hand-verified scenarios
from section 6 of the project plan, plus edge cases and invalid input
tests (ValueError checks).

Author: Kişi B
Mini Project: 01 – Capacity Calculator
"""

import json
import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calculations import (
    theoretical_capacity,
    effective_capacity,
    utilization_rate,
    capacity_gap,
    demand_fulfillment_status,
    calculate,
)


class TestTheoreticalCapacity(unittest.TestCase):
    """Tests for theoretical_capacity function."""

    def test_scenario_1_standard_shift(self):
        """8 hours, 30 sec cycle → 960 units/day."""
        result = theoretical_capacity(8, 30)
        self.assertAlmostEqual(result, 960.0, places=2)

    def test_scenario_3_double_shift(self):
        """16 hours, 45 sec cycle → 1280 units/day."""
        result = theoretical_capacity(16, 45)
        self.assertAlmostEqual(result, 1280.0, places=2)

    def test_scenario_4_long_cycle(self):
        """8 hours, 60 sec cycle → 480 units/day."""
        result = theoretical_capacity(8, 60)
        self.assertAlmostEqual(result, 480.0, places=2)

    def test_scenario_5_extended_shift(self):
        """10 hours, 20 sec cycle → 1800 units/day."""
        result = theoretical_capacity(10, 20)
        self.assertAlmostEqual(result, 1800.0, places=2)

    def test_invalid_zero_working_time(self):
        """Working time of 0 should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(0, 30)

    def test_invalid_negative_working_time(self):
        """Negative working time should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(-8, 30)

    def test_invalid_working_time_over_24(self):
        """Working time > 24 hours should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(25, 30)

    def test_invalid_zero_cycle_time(self):
        """Cycle time of 0 should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(8, 0)

    def test_invalid_negative_cycle_time(self):
        """Negative cycle time should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(8, -30)

    def test_invalid_non_numeric_working_time(self):
        """Non-numeric working time should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity("abc", 30)

    def test_invalid_non_numeric_cycle_time(self):
        """Non-numeric cycle time should raise ValueError."""
        with self.assertRaises(ValueError):
            theoretical_capacity(8, "abc")

    def test_boundary_24_hours(self):
        """24 hours is a valid boundary value."""
        result = theoretical_capacity(24, 30)
        self.assertAlmostEqual(result, 2880.0, places=2)

    def test_small_cycle_time(self):
        """Very small cycle time produces large capacity."""
        result = theoretical_capacity(8, 1)
        self.assertAlmostEqual(result, 28800.0, places=2)


class TestEffectiveCapacity(unittest.TestCase):
    """Tests for effective_capacity function."""

    def test_scenario_1_85_percent(self):
        """960 theoretical, 85% efficiency → 816."""
        result = effective_capacity(960.0, 85)
        self.assertAlmostEqual(result, 816.0, places=2)

    def test_scenario_3_90_percent(self):
        """1280 theoretical, 90% efficiency → 1152."""
        result = effective_capacity(1280.0, 90)
        self.assertAlmostEqual(result, 1152.0, places=2)

    def test_scenario_4_70_percent(self):
        """480 theoretical, 70% efficiency → 336."""
        result = effective_capacity(480.0, 70)
        self.assertAlmostEqual(result, 336.0, places=2)

    def test_scenario_5_95_percent(self):
        """1800 theoretical, 95% efficiency → 1710."""
        result = effective_capacity(1800.0, 95)
        self.assertAlmostEqual(result, 1710.0, places=2)

    def test_scenario_6_80_percent(self):
        """960 theoretical, 80% efficiency → 768."""
        result = effective_capacity(960.0, 80)
        self.assertAlmostEqual(result, 768.0, places=2)

    def test_100_percent_efficiency(self):
        """100% efficiency → effective equals theoretical."""
        result = effective_capacity(960.0, 100)
        self.assertAlmostEqual(result, 960.0, places=2)

    def test_invalid_zero_efficiency(self):
        """0% efficiency should raise ValueError."""
        with self.assertRaises(ValueError):
            effective_capacity(960.0, 0)

    def test_invalid_over_100_efficiency(self):
        """Efficiency > 100% should raise ValueError."""
        with self.assertRaises(ValueError):
            effective_capacity(960.0, 120)

    def test_invalid_negative_efficiency(self):
        """Negative efficiency should raise ValueError."""
        with self.assertRaises(ValueError):
            effective_capacity(960.0, -85)

    def test_invalid_negative_theoretical(self):
        """Negative theoretical capacity should raise ValueError."""
        with self.assertRaises(ValueError):
            effective_capacity(-960.0, 85)


class TestUtilizationRate(unittest.TestCase):
    """Tests for utilization_rate function."""

    def test_scenario_1_surplus(self):
        """700 demand / 816 effective → 85.78%."""
        result = utilization_rate(700, 816.0)
        self.assertAlmostEqual(result, 85.78, places=2)

    def test_scenario_2_deficit(self):
        """1000 demand / 816 effective → 122.55%."""
        result = utilization_rate(1000, 816.0)
        self.assertAlmostEqual(result, 122.55, places=2)

    def test_scenario_3_double_shift(self):
        """1000 demand / 1152 effective → 86.81%."""
        result = utilization_rate(1000, 1152.0)
        self.assertAlmostEqual(result, 86.81, places=2)

    def test_scenario_4_deficit(self):
        """400 demand / 336 effective → 119.05%."""
        result = utilization_rate(400, 336.0)
        self.assertAlmostEqual(result, 119.05, places=2)

    def test_scenario_5_near_limit(self):
        """1700 demand / 1710 effective → 99.42%."""
        result = utilization_rate(1700, 1710.0)
        self.assertAlmostEqual(result, 99.42, places=2)

    def test_scenario_6_exact_balance(self):
        """768 demand / 768 effective → 100.00%."""
        result = utilization_rate(768, 768.0)
        self.assertAlmostEqual(result, 100.00, places=2)

    def test_scenario_7_zero_demand(self):
        """0 demand / 816 effective → 0.00%."""
        result = utilization_rate(0, 816.0)
        self.assertAlmostEqual(result, 0.00, places=2)

    def test_invalid_negative_demand(self):
        """Negative demand should raise ValueError."""
        with self.assertRaises(ValueError):
            utilization_rate(-100, 816.0)

    def test_invalid_zero_effective(self):
        """Zero effective capacity should raise ValueError."""
        with self.assertRaises(ValueError):
            utilization_rate(100, 0)

    def test_invalid_negative_effective(self):
        """Negative effective capacity should raise ValueError."""
        with self.assertRaises(ValueError):
            utilization_rate(100, -816.0)


class TestCapacityGap(unittest.TestCase):
    """Tests for capacity_gap function."""

    def test_scenario_1_surplus(self):
        """816 effective - 700 demand = +116."""
        result = capacity_gap(816.0, 700)
        self.assertAlmostEqual(result, 116.0, places=2)

    def test_scenario_2_deficit(self):
        """816 effective - 1000 demand = -184."""
        result = capacity_gap(816.0, 1000)
        self.assertAlmostEqual(result, -184.0, places=2)

    def test_scenario_3_surplus(self):
        """1152 effective - 1000 demand = +152."""
        result = capacity_gap(1152.0, 1000)
        self.assertAlmostEqual(result, 152.0, places=2)

    def test_scenario_4_deficit(self):
        """336 effective - 400 demand = -64."""
        result = capacity_gap(336.0, 400)
        self.assertAlmostEqual(result, -64.0, places=2)

    def test_scenario_5_near_limit(self):
        """1710 effective - 1700 demand = +10."""
        result = capacity_gap(1710.0, 1700)
        self.assertAlmostEqual(result, 10.0, places=2)

    def test_scenario_6_exact_balance(self):
        """768 effective - 768 demand = 0."""
        result = capacity_gap(768.0, 768)
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_scenario_7_zero_demand(self):
        """816 effective - 0 demand = +816."""
        result = capacity_gap(816.0, 0)
        self.assertAlmostEqual(result, 816.0, places=2)

    def test_invalid_negative_effective(self):
        """Negative effective should raise ValueError."""
        with self.assertRaises(ValueError):
            capacity_gap(-816.0, 700)

    def test_invalid_negative_demand(self):
        """Negative demand should raise ValueError."""
        with self.assertRaises(ValueError):
            capacity_gap(816.0, -700)


class TestDemandFulfillmentStatus(unittest.TestCase):
    """Tests for demand_fulfillment_status function."""

    def test_surplus_returns_true(self):
        """Surplus case: demand < effective → (True, message with surplus)."""
        is_met, msg = demand_fulfillment_status(816.0, 700)
        self.assertTrue(is_met)
        self.assertIn("fazlası", msg)
        self.assertIn("116.00", msg)

    def test_exact_balance_returns_true(self):
        """Balance case: demand == effective → (True, balance message)."""
        is_met, msg = demand_fulfillment_status(768.0, 768)
        self.assertTrue(is_met)
        self.assertIn("dengede", msg)

    def test_deficit_returns_false(self):
        """Deficit case: demand > effective → (False, message with deficit)."""
        is_met, msg = demand_fulfillment_status(816.0, 1000)
        self.assertFalse(is_met)
        self.assertIn("açığı", msg)
        self.assertIn("184.00", msg)

    def test_zero_demand_returns_true(self):
        """Zero demand → (True, surplus message)."""
        is_met, msg = demand_fulfillment_status(816.0, 0)
        self.assertTrue(is_met)
        self.assertIn("fazlası", msg)

    def test_invalid_negative_effective(self):
        """Negative effective should raise ValueError."""
        with self.assertRaises(ValueError):
            demand_fulfillment_status(-816.0, 700)

    def test_invalid_negative_demand(self):
        """Negative demand should raise ValueError."""
        with self.assertRaises(ValueError):
            demand_fulfillment_status(816.0, -700)


class TestCalculate(unittest.TestCase):
    """Tests for the calculate orchestrator function."""

    def test_scenario_1_full_pipeline(self):
        """Full pipeline test with scenario 1 (surplus)."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            "efficiency_percent": 85,
            "demand_units": 700,
        }
        results = calculate(input_data)

        self.assertAlmostEqual(results["theoretical_capacity"], 960.0, places=2)
        self.assertAlmostEqual(results["effective_capacity"], 816.0, places=2)
        self.assertAlmostEqual(results["utilization_rate_percent"], 85.78, places=2)
        self.assertAlmostEqual(results["capacity_gap"], 116.0, places=2)
        self.assertTrue(results["demand_met"])
        self.assertIsInstance(results["status_message"], str)

    def test_scenario_2_full_pipeline(self):
        """Full pipeline test with scenario 2 (deficit)."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            "efficiency_percent": 85,
            "demand_units": 1000,
        }
        results = calculate(input_data)

        self.assertAlmostEqual(results["theoretical_capacity"], 960.0, places=2)
        self.assertAlmostEqual(results["effective_capacity"], 816.0, places=2)
        self.assertAlmostEqual(results["utilization_rate_percent"], 122.55, places=2)
        self.assertAlmostEqual(results["capacity_gap"], -184.0, places=2)
        self.assertFalse(results["demand_met"])

    def test_scenario_6_exact_balance(self):
        """Full pipeline test with scenario 6 (exact balance)."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            "efficiency_percent": 80,
            "demand_units": 768,
        }
        results = calculate(input_data)

        self.assertAlmostEqual(results["theoretical_capacity"], 960.0, places=2)
        self.assertAlmostEqual(results["effective_capacity"], 768.0, places=2)
        self.assertAlmostEqual(results["utilization_rate_percent"], 100.00, places=2)
        self.assertAlmostEqual(results["capacity_gap"], 0.0, places=2)
        self.assertTrue(results["demand_met"])

    def test_scenario_7_zero_demand(self):
        """Full pipeline test with scenario 7 (zero demand)."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            "efficiency_percent": 85,
            "demand_units": 0,
        }
        results = calculate(input_data)

        self.assertAlmostEqual(results["theoretical_capacity"], 960.0, places=2)
        self.assertAlmostEqual(results["effective_capacity"], 816.0, places=2)
        self.assertAlmostEqual(results["utilization_rate_percent"], 0.00, places=2)
        self.assertAlmostEqual(results["capacity_gap"], 816.0, places=2)
        self.assertTrue(results["demand_met"])

    def test_result_dict_has_all_keys(self):
        """Result dictionary must contain all 6 keys from section 2.3."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            "efficiency_percent": 85,
            "demand_units": 700,
        }
        results = calculate(input_data)

        expected_keys = {
            "theoretical_capacity",
            "effective_capacity",
            "utilization_rate_percent",
            "capacity_gap",
            "demand_met",
            "status_message",
        }
        self.assertEqual(set(results.keys()), expected_keys)

    def test_missing_key_raises_error(self):
        """Missing key in input_data should raise KeyError."""
        input_data = {
            "working_time_hours": 8,
            "cycle_time_sec": 30,
            # missing efficiency_percent and demand_units
        }
        with self.assertRaises(KeyError):
            calculate(input_data)

    def test_invalid_values_propagate_error(self):
        """Invalid values should propagate ValueError from sub-functions."""
        input_data = {
            "working_time_hours": 0,  # invalid
            "cycle_time_sec": 30,
            "efficiency_percent": 85,
            "demand_units": 700,
        }
        with self.assertRaises(ValueError):
            calculate(input_data)


class TestAllScenariosFromJSON(unittest.TestCase):
    """Load scenarios.json and verify each scenario against calculate()."""

    @classmethod
    def setUpClass(cls):
        """Load the scenarios.json file."""
        json_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "scenarios.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            cls.scenarios = json.load(f)

    def test_all_scenarios_match(self):
        """Each scenario in scenarios.json must produce matching results."""
        for scenario in self.scenarios:
            with self.subTest(name=scenario["name"]):
                results = calculate(scenario["input"])

                self.assertAlmostEqual(
                    results["theoretical_capacity"],
                    scenario["expected"]["theoretical_capacity"],
                    places=2,
                    msg=f"{scenario['name']}: theoretical_capacity mismatch",
                )
                self.assertAlmostEqual(
                    results["effective_capacity"],
                    scenario["expected"]["effective_capacity"],
                    places=2,
                    msg=f"{scenario['name']}: effective_capacity mismatch",
                )
                self.assertAlmostEqual(
                    results["utilization_rate_percent"],
                    scenario["expected"]["utilization_rate_percent"],
                    places=2,
                    msg=f"{scenario['name']}: utilization_rate_percent mismatch",
                )
                self.assertAlmostEqual(
                    results["capacity_gap"],
                    scenario["expected"]["capacity_gap"],
                    places=2,
                    msg=f"{scenario['name']}: capacity_gap mismatch",
                )
                self.assertEqual(
                    results["demand_met"],
                    scenario["expected"]["demand_met"],
                    msg=f"{scenario['name']}: demand_met mismatch",
                )


if __name__ == "__main__":
    unittest.main()
