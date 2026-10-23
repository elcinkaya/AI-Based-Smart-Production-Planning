"""
test_scenarios.py – End-to-end scenario tests from Word Section 7.

Runs all 22 scenarios from the project plan tables (7.2 and 7.3) using
the sample factory built by build_sample_factory().

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factory_model.machine import Machine, MachineStatus
from factory_model.product import Product
from factory_model.production_line import ProductionLine, find_lines_for_product
from factory_model.sample_data import build_sample_factory
from factory_model.serialization import save_factory_json, load_factory_json


class TestSampleFactory(unittest.TestCase):
    """Verify the sample factory structure from Section 7.1."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = build_sample_factory()
        cls.products = cls.factory["products"]
        cls.machines = cls.factory["machines"]
        cls.lines = cls.factory["lines"]
        # Quick lookup
        cls.m = {m.machine_id: m for m in cls.machines}
        cls.p = {p.product_code: p for p in cls.products}
        cls.l = {ln.line_id: ln for ln in cls.lines}

    def test_product_count(self) -> None:
        self.assertEqual(len(self.products), 3)

    def test_machine_count(self) -> None:
        self.assertEqual(len(self.machines), 5)

    def test_line_count(self) -> None:
        self.assertEqual(len(self.lines), 3)


# ====================================================================== #
# Section 7.2 – Machine Scenarios (1–10)
# ====================================================================== #

class TestMachineScenarios(unittest.TestCase):
    """Machine scenarios from Word Section 7.2."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = build_sample_factory()
        cls.m = {m.machine_id: m for m in cls.factory["machines"]}

    def test_scenario_01_m1_capacity(self) -> None:
        """Scenario 1: M1 theoretical=960, effective=816."""
        m1 = self.m["M1"]
        self.assertAlmostEqual(m1.get_theoretical_capacity(), 960.0, places=2)
        self.assertAlmostEqual(m1.get_effective_capacity(), 816.0, places=2)

    def test_scenario_02_m2_capacity(self) -> None:
        """Scenario 2: M2 (IDLE) theoretical=1280, effective=1152."""
        m2 = self.m["M2"]
        self.assertTrue(m2.is_available())
        self.assertAlmostEqual(m2.get_theoretical_capacity(), 1280.0, places=2)
        self.assertAlmostEqual(m2.get_effective_capacity(), 1152.0, places=2)

    def test_scenario_03_m4_broken(self) -> None:
        """Scenario 3: M4 (BROKEN) theoretical=1800, effective=0.0, not available."""
        m4 = self.m["M4"]
        self.assertAlmostEqual(m4.get_theoretical_capacity(), 1800.0, places=2)
        self.assertEqual(m4.get_effective_capacity(), 0.0)
        self.assertFalse(m4.is_available())

    def test_scenario_04_m4_repair(self) -> None:
        """Scenario 4: M4 BROKEN→MAINTENANCE→perform → IDLE, counter=0, eff=1710."""
        # Use a fresh factory to avoid state corruption
        factory = build_sample_factory()
        m4 = {m.machine_id: m for m in factory["machines"]}["M4"]
        m4.set_status(MachineStatus.MAINTENANCE)
        m4.perform_maintenance()
        self.assertEqual(m4.status, MachineStatus.IDLE)
        self.assertEqual(m4.operating_hours_since_maintenance, 0.0)
        self.assertAlmostEqual(m4.get_effective_capacity(), 1710.0, places=2)

    def test_scenario_05_needs_maintenance(self) -> None:
        """Scenario 5: M1=False, M2=True (205≥200), M3=False."""
        self.assertFalse(self.m["M1"].needs_maintenance())
        self.assertTrue(self.m["M2"].needs_maintenance())
        self.assertFalse(self.m["M3"].needs_maintenance())

    def test_scenario_06_add_hours(self) -> None:
        """Scenario 6: M1 + 150h → counter=200, needs_maintenance=True."""
        factory = build_sample_factory()
        m1 = {m.machine_id: m for m in factory["machines"]}["M1"]
        m1.add_operating_hours(150)
        self.assertEqual(m1.operating_hours_since_maintenance, 200.0)
        self.assertTrue(m1.needs_maintenance())

    def test_scenario_07_add_hours_idle_raises(self) -> None:
        """Scenario 7: M5 (IDLE) add_operating_hours(5) → ValueError."""
        with self.assertRaises(ValueError):
            self.m["M5"].add_operating_hours(5)

    def test_scenario_08_broken_to_running_raises(self) -> None:
        """Scenario 8: BROKEN → RUNNING is not allowed."""
        factory = build_sample_factory()
        m3 = {m.machine_id: m for m in factory["machines"]}["M3"]
        m3.set_status(MachineStatus.BROKEN)
        with self.assertRaises(ValueError):
            m3.set_status(MachineStatus.RUNNING)

    def test_scenario_09_custom_cycle_time(self) -> None:
        """Scenario 9: M1 with cycle_time_sec=45 → theoretical=640, effective=544."""
        m1 = self.m["M1"]
        self.assertAlmostEqual(
            m1.get_theoretical_capacity(cycle_time_sec=45), 640.0, places=2,
        )
        self.assertAlmostEqual(
            m1.get_effective_capacity(cycle_time_sec=45), 544.0, places=2,
        )

    def test_scenario_10_round_trip(self) -> None:
        """Scenario 10: M4 to_dict → from_dict, status='broken', equal."""
        m4 = self.m["M4"]
        d = m4.to_dict()
        self.assertEqual(d["status"], "broken")
        m4_copy = Machine.from_dict(d)
        self.assertEqual(m4_copy.to_dict(), d)


# ====================================================================== #
# Section 7.3 – Line and Relationship Scenarios (11–22)
# ====================================================================== #

class TestLineScenarios(unittest.TestCase):
    """Line and relationship scenarios from Word Section 7.3."""

    def _fresh_factory(self):
        """Build a fresh factory for each test that mutates state."""
        f = build_sample_factory()
        m = {m.machine_id: m for m in f["machines"]}
        p = {p.product_code: p for p in f["products"]}
        l = {ln.line_id: ln for ln in f["lines"]}
        return f, m, p, l

    def test_scenario_11_line_capacities(self) -> None:
        """Scenario 11: L1=1968, L2=336, L3=768 (no product)."""
        _, _, _, l = self._fresh_factory()
        self.assertAlmostEqual(l["L1"].get_effective_capacity(), 1968.0, places=2)
        self.assertAlmostEqual(l["L2"].get_effective_capacity(), 336.0, places=2)
        self.assertAlmostEqual(l["L3"].get_effective_capacity(), 768.0, places=2)

    def test_scenario_12_l1_product_capacity(self) -> None:
        """Scenario 12: L1 with P-A=2544, P-B=1696."""
        _, _, p, l = self._fresh_factory()
        self.assertAlmostEqual(
            l["L1"].get_effective_capacity(p["P-A"]), 2544.0, places=2,
        )
        self.assertAlmostEqual(
            l["L1"].get_effective_capacity(p["P-B"]), 1696.0, places=2,
        )

    def test_scenario_13_l2_product_capacity(self) -> None:
        """Scenario 13: L2 with P-B=448, P-C=336."""
        _, _, p, l = self._fresh_factory()
        self.assertAlmostEqual(
            l["L2"].get_effective_capacity(p["P-B"]), 448.0, places=2,
        )
        self.assertAlmostEqual(
            l["L2"].get_effective_capacity(p["P-C"]), 336.0, places=2,
        )

    def test_scenario_14_l3_product_capacity(self) -> None:
        """Scenario 14: L3 with P-A=768, P-C=384."""
        _, _, p, l = self._fresh_factory()
        self.assertAlmostEqual(
            l["L3"].get_effective_capacity(p["P-A"]), 768.0, places=2,
        )
        self.assertAlmostEqual(
            l["L3"].get_effective_capacity(p["P-C"]), 384.0, places=2,
        )

    def test_scenario_15_incompatible_product(self) -> None:
        """Scenario 15: L2 + P-A → is_compatible=False, get_effective_capacity raises."""
        _, _, p, l = self._fresh_factory()
        self.assertFalse(l["L2"].is_compatible(p["P-A"]))
        with self.assertRaises(ValueError):
            l["L2"].get_effective_capacity(p["P-A"])

    def test_scenario_16_find_lines_for_product(self) -> None:
        """Scenario 16: P-A=[L1,L3], P-B=[L1,L2], P-C=[L2,L3]."""
        f, _, p, _ = self._fresh_factory()
        lines = f["lines"]

        result_a = [ln.line_id for ln in find_lines_for_product(p["P-A"], lines)]
        result_b = [ln.line_id for ln in find_lines_for_product(p["P-B"], lines)]
        result_c = [ln.line_id for ln in find_lines_for_product(p["P-C"], lines)]

        self.assertEqual(result_a, ["L1", "L3"])
        self.assertEqual(result_b, ["L1", "L2"])
        self.assertEqual(result_c, ["L2", "L3"])

    def test_scenario_17_repair_and_capacity(self) -> None:
        """Scenario 17: After M4 repair, L2 (no product) = 336+1710 = 2046."""
        _, m, _, l = self._fresh_factory()
        # M4 is BROKEN → repair
        m["M4"].set_status(MachineStatus.MAINTENANCE)
        m["M4"].perform_maintenance()
        self.assertAlmostEqual(
            l["L2"].get_effective_capacity(), 2046.0, places=2,
        )

    def test_scenario_18_machines_needing_maintenance(self) -> None:
        """Scenario 18: L1=[M2], L2=[], L3=[]."""
        _, _, _, l = self._fresh_factory()
        l1_needing = [m.machine_id for m in l["L1"].get_machines_needing_maintenance()]
        l2_needing = [m.machine_id for m in l["L2"].get_machines_needing_maintenance()]
        l3_needing = [m.machine_id for m in l["L3"].get_machines_needing_maintenance()]
        self.assertEqual(l1_needing, ["M2"])
        self.assertEqual(l2_needing, [])
        self.assertEqual(l3_needing, [])

    def test_scenario_19_add_errors(self) -> None:
        """Scenario 19: duplicate M1, M1 to L2, non-Machine → errors."""
        _, m, _, l = self._fresh_factory()
        # M1 already in L1 → add again to L1
        with self.assertRaises(ValueError):
            l["L1"].add_machine(m["M1"])
        # M1 belongs to L1 → add to L2
        with self.assertRaises(ValueError):
            l["L2"].add_machine(m["M1"])
        # Non-Machine object
        with self.assertRaises(TypeError):
            l["L1"].add_machine("not a machine")  # type: ignore[arg-type]

    def test_scenario_20_remove_machine(self) -> None:
        """Scenario 20: remove M2 from L1 → M2.line_id=None, L1 eff=816."""
        _, m, _, l = self._fresh_factory()
        removed = l["L1"].remove_machine("M2")
        self.assertIsNone(removed.line_id)
        self.assertAlmostEqual(l["L1"].get_effective_capacity(), 816.0, places=2)

    def test_scenario_21_json_round_trip(self) -> None:
        """Scenario 21: save → load → capacities match scenarios 11–14."""
        f, _, _, _ = self._fresh_factory()
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "test_factory.json")

        save_factory_json(path, f["products"], f["machines"], f["lines"])
        loaded = load_factory_json(path)

        loaded_lines = {ln.line_id: ln for ln in loaded["lines"]}

        # Scenario 11 capacities
        self.assertAlmostEqual(
            loaded_lines["L1"].get_effective_capacity(), 1968.0, places=2,
        )
        self.assertAlmostEqual(
            loaded_lines["L2"].get_effective_capacity(), 336.0, places=2,
        )
        self.assertAlmostEqual(
            loaded_lines["L3"].get_effective_capacity(), 768.0, places=2,
        )

        # Scenario 12–14 product-specific capacities
        loaded_products = {p.product_code: p for p in loaded["products"]}
        self.assertAlmostEqual(
            loaded_lines["L1"].get_effective_capacity(loaded_products["P-A"]),
            2544.0, places=2,
        )
        self.assertAlmostEqual(
            loaded_lines["L1"].get_effective_capacity(loaded_products["P-B"]),
            1696.0, places=2,
        )

    def test_scenario_22_to_dict_keys(self) -> None:
        """Scenario 22: All three classes' to_dict() keys match Section 3.4."""
        f, _, _, _ = self._fresh_factory()

        # Product
        p = f["products"][0]
        self.assertEqual(
            set(p.to_dict().keys()),
            {"product_code", "name", "processing_time_sec", "priority"},
        )

        # Machine
        m = f["machines"][0]
        self.assertEqual(
            set(m.to_dict().keys()),
            {
                "machine_id", "name", "working_hours", "cycle_time_sec",
                "efficiency_pct", "maintenance_interval_hours", "status",
                "operating_hours_since_maintenance", "line_id",
            },
        )

        # ProductionLine
        ln = f["lines"][0]
        self.assertEqual(
            set(ln.to_dict().keys()),
            {"line_id", "name", "machine_ids", "compatible_product_codes"},
        )


# ====================================================================== #
# Section 7.4 – Error/Invalid Input Tests (C's responsibility)
# ====================================================================== #

class TestInvalidInputScenarios(unittest.TestCase):
    """Invalid input tests from Section 7.4 – line-related."""

    def test_add_non_machine_to_line(self) -> None:
        """Hat: Machine olmayan nesne eklemek → TypeError."""
        line = ProductionLine("L1", "Test")
        with self.assertRaises(TypeError):
            line.add_machine(42)  # type: ignore[arg-type]

    def test_query_nonexistent_machine(self) -> None:
        """Hat: var olmayan machine_id sorgulamak → ValueError."""
        line = ProductionLine("L1", "Test")
        with self.assertRaises(ValueError):
            line.get_machine("M99")

    def test_from_dict_missing_line_id(self) -> None:
        """from_dict: line_id eksik → ValueError."""
        data = {"name": "X", "machine_ids": [], "compatible_product_codes": []}
        with self.assertRaises(ValueError) as ctx:
            ProductionLine.from_dict(data, {})
        self.assertIn("line_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
