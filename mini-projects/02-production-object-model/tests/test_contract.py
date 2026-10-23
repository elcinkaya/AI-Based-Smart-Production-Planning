"""
test_contract.py – Data-contract key verification for all entity classes.

Ensures that every class's ``to_dict()`` output has exactly the keys
defined in the Section 3.4 data contract, with no extra or missing keys.

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factory_model.product import Product
from factory_model.machine import Machine, MachineStatus
from factory_model.production_line import ProductionLine


class TestProductContract(unittest.TestCase):
    """Verify Product.to_dict() keys match Section 3.4."""

    EXPECTED_KEYS = {"product_code", "name", "processing_time_sec", "priority"}

    def test_to_dict_keys(self) -> None:
        p = Product("P-A", "Bracket", 30.0, 1)
        self.assertEqual(set(p.to_dict().keys()), self.EXPECTED_KEYS)

    def test_to_dict_key_count(self) -> None:
        p = Product("P-B", "Shaft", 45.0, 2)
        self.assertEqual(len(p.to_dict()), len(self.EXPECTED_KEYS))


class TestMachineContract(unittest.TestCase):
    """Verify Machine.to_dict() keys match Section 3.4."""

    EXPECTED_KEYS = {
        "machine_id", "name", "working_hours", "cycle_time_sec",
        "efficiency_pct", "maintenance_interval_hours", "status",
        "operating_hours_since_maintenance", "line_id",
    }

    def test_to_dict_keys(self) -> None:
        m = Machine(
            machine_id="M1", name="CNC Lathe 1",
            working_hours=8, cycle_time_sec=30, efficiency_pct=85,
            maintenance_interval_hours=200,
            status=MachineStatus.RUNNING,
            operating_hours_since_maintenance=50,
            line_id="L1",
        )
        self.assertEqual(set(m.to_dict().keys()), self.EXPECTED_KEYS)

    def test_to_dict_key_count(self) -> None:
        m = Machine("M1", "T", 8, 30, 85, 200)
        self.assertEqual(len(m.to_dict()), len(self.EXPECTED_KEYS))

    def test_status_is_string(self) -> None:
        """Status value must be a plain string, not a MachineStatus enum."""
        m = Machine("M1", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        d = m.to_dict()
        self.assertIsInstance(d["status"], str)
        self.assertEqual(d["status"], "broken")


class TestProductionLineContract(unittest.TestCase):
    """Verify ProductionLine.to_dict() keys match Section 3.4."""

    EXPECTED_KEYS = {
        "line_id", "name", "machine_ids", "compatible_product_codes",
    }

    def _build_line(self) -> ProductionLine:
        line = ProductionLine("L1", "Machining Line")
        m = Machine("M1", "T", 8, 30, 85, 200)
        line.add_machine(m)
        p = Product("P-A", "Bracket", 30.0, 1)
        line.add_compatible_product(p)
        return line

    def test_to_dict_keys(self) -> None:
        line = self._build_line()
        self.assertEqual(set(line.to_dict().keys()), self.EXPECTED_KEYS)

    def test_to_dict_key_count(self) -> None:
        line = self._build_line()
        self.assertEqual(len(line.to_dict()), len(self.EXPECTED_KEYS))

    def test_machine_ids_is_list(self) -> None:
        line = self._build_line()
        d = line.to_dict()
        self.assertIsInstance(d["machine_ids"], list)

    def test_compatible_product_codes_is_sorted_list(self) -> None:
        line = ProductionLine("L1", "Test")
        p_c = Product("P-C", "Housing", 60.0, 3)
        p_a = Product("P-A", "Bracket", 30.0, 1)
        line.add_compatible_product(p_c)
        line.add_compatible_product(p_a)
        d = line.to_dict()
        self.assertIsInstance(d["compatible_product_codes"], list)
        self.assertEqual(d["compatible_product_codes"], ["P-A", "P-C"])


if __name__ == "__main__":
    unittest.main()
