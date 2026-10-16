"""
Unit tests for the inputs module (Kişi A).

Tests cover:
  * Empty input handling
  * Non-numeric input (letters, symbols)
  * Negative values
  * Boundary values (0, 24, 100)
  * Out-of-range values
  * Decimal-comma acceptance (e.g. "7,5")
  * Correct dictionary keys from get_user_inputs()

All tests use unittest.mock.patch to simulate user input via stdin.
"""

import unittest
from unittest.mock import patch

# inputs.py is one level up; adjust the import path accordingly.
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from inputs import get_number, get_user_inputs


class TestGetNumber(unittest.TestCase):
    """Tests for inputs.get_number()."""

    # ------------------------------------------------------------------ #
    # Happy-path tests
    # ------------------------------------------------------------------ #
    @patch("builtins.input", return_value="8")
    def test_valid_integer(self, _mock):
        """A plain integer string should be accepted."""
        result = get_number("test: ", min_value=0, max_value=24,
                            min_inclusive=False, max_inclusive=True)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", return_value="7.5")
    def test_valid_float_dot(self, _mock):
        """A dot-decimal float should be accepted."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 7.5)

    @patch("builtins.input", return_value="7,5")
    def test_valid_float_comma(self, _mock):
        """A comma-decimal float (Turkish style) should be accepted."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 7.5)

    @patch("builtins.input", return_value="24")
    def test_upper_boundary_inclusive(self, _mock):
        """Value equal to max_value should be accepted when max_inclusive=True."""
        result = get_number("test: ", min_value=0, max_value=24,
                            min_inclusive=False, max_inclusive=True)
        self.assertEqual(result, 24.0)

    @patch("builtins.input", return_value="0")
    def test_lower_boundary_inclusive(self, _mock):
        """Value equal to min_value should be accepted when min_inclusive=True."""
        result = get_number("test: ", min_value=0, min_inclusive=True)
        self.assertEqual(result, 0.0)

    @patch("builtins.input", return_value="0.01")
    def test_just_above_zero_exclusive(self, _mock):
        """A tiny positive value should pass when min=0 exclusive."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertAlmostEqual(result, 0.01)

    # ------------------------------------------------------------------ #
    # Invalid-input tests (function re-asks, we supply valid after bad)
    # ------------------------------------------------------------------ #
    @patch("builtins.input", side_effect=["", "8"])
    def test_empty_then_valid(self, _mock):
        """Empty input should trigger a warning; next valid input accepted."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["abc", "8"])
    def test_letters_then_valid(self, _mock):
        """Alphabetic input should be rejected."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["8h", "8"])
    def test_alphanumeric_then_valid(self, _mock):
        """Mixed alpha-numeric input should be rejected."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["-5", "8"])
    def test_negative_then_valid(self, _mock):
        """Negative value should be rejected when min_value=0 exclusive."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["0", "8"])
    def test_zero_rejected_exclusive(self, _mock):
        """Zero should be rejected when min_value=0 and min_inclusive=False."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["25", "8"])
    def test_above_max_then_valid(self, _mock):
        """Value above max should be rejected."""
        result = get_number("test: ", min_value=0, max_value=24,
                            min_inclusive=False, max_inclusive=True)
        self.assertEqual(result, 8.0)

    @patch("builtins.input", side_effect=["120", "85"])
    def test_efficiency_over_100(self, _mock):
        """Efficiency > 100 should be rejected."""
        result = get_number("test: ", min_value=0, max_value=100,
                            min_inclusive=False, max_inclusive=True)
        self.assertEqual(result, 85.0)

    @patch("builtins.input", side_effect=["-50", "0"])
    def test_negative_demand_then_zero(self, _mock):
        """Negative demand should be rejected; zero demand is valid."""
        result = get_number("test: ", min_value=0, min_inclusive=True)
        self.assertEqual(result, 0.0)

    @patch("builtins.input", side_effect=["", "abc", "-1", "0", "5"])
    def test_multiple_retries(self, _mock):
        """Multiple invalid inputs followed by a valid one."""
        result = get_number("test: ", min_value=0, min_inclusive=False)
        self.assertEqual(result, 5.0)

    # ------------------------------------------------------------------ #
    # No-bounds test
    # ------------------------------------------------------------------ #
    @patch("builtins.input", return_value="-999")
    def test_no_bounds(self, _mock):
        """When no bounds are given, any number should be accepted."""
        result = get_number("test: ")
        self.assertEqual(result, -999.0)


class TestGetUserInputs(unittest.TestCase):
    """Tests for inputs.get_user_inputs()."""

    @patch("builtins.input", side_effect=["8", "30", "85", "700"])
    def test_returns_correct_keys(self, _mock):
        """Returned dict must have exactly the four data-contract keys."""
        result = get_user_inputs()
        expected_keys = {
            "working_time_hours",
            "cycle_time_sec",
            "efficiency_percent",
            "demand_units",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    @patch("builtins.input", side_effect=["8", "30", "85", "700"])
    def test_returns_correct_values(self, _mock):
        """Scenario 1 inputs should produce matching float values."""
        result = get_user_inputs()
        self.assertEqual(result["working_time_hours"], 8.0)
        self.assertEqual(result["cycle_time_sec"], 30.0)
        self.assertEqual(result["efficiency_percent"], 85.0)
        self.assertEqual(result["demand_units"], 700.0)

    @patch("builtins.input", side_effect=["16", "45", "90", "1000"])
    def test_scenario3_inputs(self, _mock):
        """Scenario 3 (double-shift) inputs."""
        result = get_user_inputs()
        self.assertEqual(result["working_time_hours"], 16.0)
        self.assertEqual(result["cycle_time_sec"], 45.0)
        self.assertEqual(result["efficiency_percent"], 90.0)
        self.assertEqual(result["demand_units"], 1000.0)

    @patch("builtins.input", side_effect=["8", "30", "85", "0"])
    def test_zero_demand_accepted(self, _mock):
        """Zero demand is valid (scenario 7)."""
        result = get_user_inputs()
        self.assertEqual(result["demand_units"], 0.0)

    @patch("builtins.input", side_effect=["7,5", "30", "85", "700"])
    def test_comma_decimal_working_time(self, _mock):
        """Turkish-style comma decimal should be accepted for working time."""
        result = get_user_inputs()
        self.assertEqual(result["working_time_hours"], 7.5)

    @patch("builtins.input", side_effect=[
        "",       # empty → retry working_time
        "abc",    # letters → retry working_time
        "8",      # valid working_time
        "0",      # 0 → retry cycle_time (must be > 0)
        "30",     # valid cycle_time
        "120",    # 120 → retry efficiency (must be ≤ 100)
        "85",     # valid efficiency
        "-50",    # negative → retry demand (must be ≥ 0)
        "700",    # valid demand
    ])
    def test_invalid_inputs_then_valid(self, _mock):
        """Multiple invalid entries across all four prompts."""
        result = get_user_inputs()
        self.assertEqual(result["working_time_hours"], 8.0)
        self.assertEqual(result["cycle_time_sec"], 30.0)
        self.assertEqual(result["efficiency_percent"], 85.0)
        self.assertEqual(result["demand_units"], 700.0)

    @patch("builtins.input", side_effect=["24", "0.1", "100", "0"])
    def test_boundary_values(self, _mock):
        """All boundary values should be accepted."""
        result = get_user_inputs()
        self.assertEqual(result["working_time_hours"], 24.0)
        self.assertEqual(result["cycle_time_sec"], 0.1)
        self.assertEqual(result["efficiency_percent"], 100.0)
        self.assertEqual(result["demand_units"], 0.0)

    @patch("builtins.input", side_effect=["8", "30", "85", "700"])
    def test_return_types_are_float(self, _mock):
        """All values in the returned dict must be floats."""
        result = get_user_inputs()
        for key, val in result.items():
            self.assertIsInstance(val, float, f"{key} should be float")


if __name__ == "__main__":
    unittest.main()
