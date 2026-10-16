"""
End-to-end scenario tests – reads scenarios.json and runs each scenario
through the calculate + build_report pipeline.

Verifies that all 7 scenarios produce the expected numerical results
and that the report string is generated without errors.

Author: Person C
"""

import json
import os
import sys
import unittest

# Add the project root to the path so we can import the modules
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..")
)

import calculations
import report


class TestScenarios(unittest.TestCase):
    """End-to-end tests using scenarios.json."""

    @classmethod
    def setUpClass(cls):
        """Load scenarios from the JSON file."""
        scenarios_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "scenarios.json"
        )
        with open(scenarios_path, "r", encoding="utf-8") as f:
            cls.scenarios = json.load(f)

    def test_all_scenarios_loaded(self):
        """Ensure at least 5 scenarios are loaded (requirement)."""
        self.assertGreaterEqual(
            len(self.scenarios), 5,
            "En az 5 senaryo gerekli."
        )

    def test_scenario_calculations(self):
        """Verify each scenario produces the expected results."""
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario["name"]):
                input_data = scenario["input"]
                expected = scenario["expected"]

                results = calculations.calculate(input_data)

                self.assertAlmostEqual(
                    results["theoretical_capacity"],
                    expected["theoretical_capacity"],
                    places=0,
                    msg=f"{scenario['name']}: theoretical_capacity mismatch"
                )

                self.assertAlmostEqual(
                    results["effective_capacity"],
                    expected["effective_capacity"],
                    places=0,
                    msg=f"{scenario['name']}: effective_capacity mismatch"
                )

                self.assertAlmostEqual(
                    results["utilization_rate_percent"],
                    expected["utilization_rate_percent"],
                    places=1,
                    msg=f"{scenario['name']}: utilization_rate_percent mismatch"
                )

                self.assertAlmostEqual(
                    results["capacity_gap"],
                    expected["capacity_gap"],
                    places=0,
                    msg=f"{scenario['name']}: capacity_gap mismatch"
                )

                self.assertEqual(
                    results["demand_met"],
                    expected["demand_met"],
                    msg=f"{scenario['name']}: demand_met mismatch"
                )

    def test_scenario_report_generation(self):
        """Verify that build_report produces a non-empty string for each scenario."""
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario["name"]):
                input_data = scenario["input"]
                results = calculations.calculate(input_data)
                report_text = report.build_report(input_data, results)

                self.assertIsInstance(report_text, str)
                self.assertGreater(len(report_text), 0)

                # Check that the report contains key sections
                self.assertIn("ÜRETİM KAPASİTE RAPORU", report_text)
                self.assertIn("Girdiler", report_text)
                self.assertIn("Sonuçlar", report_text)
                self.assertIn("DURUM", report_text)

    def test_scenario_report_contains_values(self):
        """Verify the report includes calculated numerical values."""
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario["name"]):
                input_data = scenario["input"]
                results = calculations.calculate(input_data)
                report_text = report.build_report(input_data, results)

                # The theoretical capacity value should appear in the report
                self.assertIn(
                    f"{results['theoretical_capacity']:.2f}",
                    report_text,
                    msg=f"{scenario['name']}: theoretical_capacity not in report"
                )

                # The effective capacity value should appear in the report
                self.assertIn(
                    f"{results['effective_capacity']:.2f}",
                    report_text,
                    msg=f"{scenario['name']}: effective_capacity not in report"
                )

    def test_surplus_scenario_status(self):
        """Verify surplus scenarios report 'KARŞILANIYOR'."""
        surplus_scenarios = [
            s for s in self.scenarios if s["expected"]["demand_met"] is True
            and s["expected"]["capacity_gap"] > 0
        ]
        for scenario in surplus_scenarios:
            with self.subTest(scenario=scenario["name"]):
                results = calculations.calculate(scenario["input"])
                self.assertIn("KARŞILANIYOR", results["status_message"])

    def test_deficit_scenario_status(self):
        """Verify deficit scenarios report 'KARŞILANMIYOR'."""
        deficit_scenarios = [
            s for s in self.scenarios if s["expected"]["demand_met"] is False
        ]
        for scenario in deficit_scenarios:
            with self.subTest(scenario=scenario["name"]):
                results = calculations.calculate(scenario["input"])
                self.assertIn("KARŞILANMIYOR", results["status_message"])

    def test_exact_balance_scenario(self):
        """Verify the exact balance scenario (capacity_gap == 0)."""
        balance_scenarios = [
            s for s in self.scenarios if s["expected"]["capacity_gap"] == 0
        ]
        for scenario in balance_scenarios:
            with self.subTest(scenario=scenario["name"]):
                results = calculations.calculate(scenario["input"])
                self.assertTrue(results["demand_met"])
                self.assertEqual(results["capacity_gap"], 0)


if __name__ == "__main__":
    unittest.main()
