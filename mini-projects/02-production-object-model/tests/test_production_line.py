"""
test_production_line.py – Unit tests for ProductionLine and find_lines_for_product.

Covers machine add/remove rules, compatibility queries, capacity
calculations (with and without product), maintenance listing, and
to_dict/from_dict round-trip serialization.

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

import os
import sys
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factory_model.base import FactoryEntity
from factory_model.machine import Machine, MachineStatus
from factory_model.product import Product
from factory_model.production_line import ProductionLine, find_lines_for_product


# ====================================================================== #
# Helpers
# ====================================================================== #

def _make_machine(
    machine_id: str = "M1",
    name: str = "Test Machine",
    working_hours: float = 8.0,
    cycle_time_sec: float = 30.0,
    efficiency_pct: float = 85.0,
    maintenance_interval_hours: float = 200.0,
    status: MachineStatus = MachineStatus.IDLE,
    operating_hours_since_maintenance: float = 0.0,
    line_id: str | None = None,
) -> Machine:
    """Create a Machine with sensible defaults for testing."""
    return Machine(
        machine_id=machine_id,
        name=name,
        working_hours=working_hours,
        cycle_time_sec=cycle_time_sec,
        efficiency_pct=efficiency_pct,
        maintenance_interval_hours=maintenance_interval_hours,
        status=status,
        operating_hours_since_maintenance=operating_hours_since_maintenance,
        line_id=line_id,
    )


def _make_product(
    product_code: str = "P-A",
    name: str = "Bracket",
    processing_time_sec: float = 30.0,
    priority: int = 1,
) -> Product:
    """Create a Product with sensible defaults for testing."""
    return Product(product_code, name, processing_time_sec, priority)


# ====================================================================== #
# 1. Construction and inheritance
# ====================================================================== #

class TestProductionLineCreation(unittest.TestCase):
    """Tests for ProductionLine construction."""

    def test_valid_creation(self) -> None:
        line = ProductionLine("L1", "Machining Line")
        self.assertEqual(line.line_id, "L1")
        self.assertEqual(line.name, "Machining Line")

    def test_inherits_factory_entity(self) -> None:
        line = ProductionLine("L1", "Test")
        self.assertIsInstance(line, FactoryEntity)

    def test_empty_line_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            ProductionLine("", "Test")

    def test_empty_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            ProductionLine("L1", "")

    def test_non_string_line_id_raises(self) -> None:
        with self.assertRaises(TypeError):
            ProductionLine(123, "Test")  # type: ignore[arg-type]

    def test_repr_readable(self) -> None:
        line = ProductionLine("L1", "Test")
        r = repr(line)
        self.assertIn("L1", r)
        self.assertIn("ProductionLine", r)


# ====================================================================== #
# 2. Machine management
# ====================================================================== #

class TestMachineManagement(unittest.TestCase):
    """Tests for add_machine, remove_machine, get_machine."""

    def test_add_machine(self) -> None:
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1")
        line.add_machine(m)
        self.assertEqual(m.line_id, "L1")
        self.assertEqual(line.get_machine("M1").machine_id, "M1")

    def test_add_non_machine_raises_type_error(self) -> None:
        """Scenario 19 (partial): Adding non-Machine raises TypeError."""
        line = ProductionLine("L1", "Test")
        with self.assertRaises(TypeError):
            line.add_machine("not a machine")  # type: ignore[arg-type]

    def test_add_duplicate_machine_raises(self) -> None:
        """Scenario 19 (partial): Adding M1 twice raises ValueError."""
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1")
        line.add_machine(m)
        with self.assertRaises(ValueError):
            line.add_machine(m)

    def test_add_machine_from_another_line_raises(self) -> None:
        """Scenario 19 (partial): Adding M1 (line_id=L1) to L2 raises ValueError."""
        l1 = ProductionLine("L1", "Line 1")
        l2 = ProductionLine("L2", "Line 2")
        m = _make_machine("M1")
        l1.add_machine(m)
        with self.assertRaises(ValueError):
            l2.add_machine(m)

    def test_remove_machine(self) -> None:
        """Scenario 20: remove_machine returns machine with line_id=None."""
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1")
        line.add_machine(m)
        removed = line.remove_machine("M1")
        self.assertIsNone(removed.line_id)
        self.assertEqual(removed.machine_id, "M1")

    def test_remove_nonexistent_machine_raises(self) -> None:
        line = ProductionLine("L1", "Test")
        with self.assertRaises(ValueError):
            line.remove_machine("M99")

    def test_get_machine_found(self) -> None:
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1")
        line.add_machine(m)
        result = line.get_machine("M1")
        self.assertIs(result, m)

    def test_get_machine_not_found_raises(self) -> None:
        line = ProductionLine("L1", "Test")
        with self.assertRaises(ValueError):
            line.get_machine("M99")


# ====================================================================== #
# 3. Product compatibility
# ====================================================================== #

class TestProductCompatibility(unittest.TestCase):
    """Tests for add_compatible_product and is_compatible."""

    def test_add_and_check_compatible(self) -> None:
        line = ProductionLine("L1", "Test")
        p = _make_product("P-A")
        line.add_compatible_product(p)
        self.assertTrue(line.is_compatible(p))

    def test_not_compatible(self) -> None:
        line = ProductionLine("L1", "Test")
        p = _make_product("P-A")
        self.assertFalse(line.is_compatible(p))

    def test_add_non_product_raises(self) -> None:
        line = ProductionLine("L1", "Test")
        with self.assertRaises(TypeError):
            line.add_compatible_product("not a product")  # type: ignore[arg-type]

    def test_add_same_product_twice_no_error(self) -> None:
        """Adding the same product code twice is idempotent (set behavior)."""
        line = ProductionLine("L1", "Test")
        p = _make_product("P-A")
        line.add_compatible_product(p)
        line.add_compatible_product(p)  # no error
        self.assertTrue(line.is_compatible(p))


# ====================================================================== #
# 4. Availability
# ====================================================================== #

class TestGetAvailableMachines(unittest.TestCase):
    """Tests for get_available_machines."""

    def test_available_machines(self) -> None:
        line = ProductionLine("L1", "Test")
        m_idle = _make_machine("M1", status=MachineStatus.IDLE)
        m_running = _make_machine("M2", status=MachineStatus.RUNNING)
        m_broken = _make_machine("M3", status=MachineStatus.BROKEN)
        for m in (m_idle, m_running, m_broken):
            line.add_machine(m)
        avail = line.get_available_machines()
        self.assertEqual(len(avail), 2)
        ids = {m.machine_id for m in avail}
        self.assertEqual(ids, {"M1", "M2"})


# ====================================================================== #
# 5. Capacity calculations
# ====================================================================== #

class TestLineCapacity(unittest.TestCase):
    """Tests for get_effective_capacity (with and without product)."""

    def test_single_machine_capacity(self) -> None:
        """Simple case: one available machine."""
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1", working_hours=8, cycle_time_sec=30,
                          efficiency_pct=85, status=MachineStatus.RUNNING)
        line.add_machine(m)
        # Expected: theoretical=960, effective=816
        self.assertAlmostEqual(line.get_effective_capacity(), 816.0, places=2)

    def test_two_machines_parallel(self) -> None:
        """Two available machines: capacities are summed."""
        line = ProductionLine("L1", "Test")
        m1 = _make_machine("M1", working_hours=8, cycle_time_sec=30,
                           efficiency_pct=85, status=MachineStatus.RUNNING)
        m2 = _make_machine("M2", working_hours=16, cycle_time_sec=45,
                           efficiency_pct=90, status=MachineStatus.IDLE)
        line.add_machine(m1)
        line.add_machine(m2)
        # M1: 816, M2: 1152 → total 1968
        self.assertAlmostEqual(line.get_effective_capacity(), 1968.0, places=2)

    def test_broken_machine_excluded(self) -> None:
        """Broken machine contributes 0.0 to line capacity."""
        line = ProductionLine("L1", "Test")
        m1 = _make_machine("M1", working_hours=8, cycle_time_sec=60,
                           efficiency_pct=70, status=MachineStatus.RUNNING)
        m2 = _make_machine("M2", working_hours=10, cycle_time_sec=20,
                           efficiency_pct=95, status=MachineStatus.BROKEN)
        line.add_machine(m1)
        line.add_machine(m2)
        # M1: theo=480, eff=336; M2: 0.0 → total 336
        self.assertAlmostEqual(line.get_effective_capacity(), 336.0, places=2)

    def test_capacity_with_product(self) -> None:
        """Product-specific capacity uses product's processing_time_sec."""
        line = ProductionLine("L1", "Test")
        m1 = _make_machine("M1", working_hours=8, cycle_time_sec=30,
                           efficiency_pct=85, status=MachineStatus.RUNNING)
        m2 = _make_machine("M2", working_hours=16, cycle_time_sec=45,
                           efficiency_pct=90, status=MachineStatus.IDLE)
        line.add_machine(m1)
        line.add_machine(m2)

        p_a = _make_product("P-A", processing_time_sec=30)
        line.add_compatible_product(p_a)

        # M1: theo=8*3600/30=960, eff=960*0.85=816
        # M2: theo=16*3600/30=1920, eff=1920*0.90=1728
        # Total: 2544
        self.assertAlmostEqual(
            line.get_effective_capacity(p_a), 2544.0, places=2,
        )

    def test_capacity_incompatible_product_raises(self) -> None:
        """Scenario 15: get_effective_capacity with incompatible product raises."""
        line = ProductionLine("L2", "Test")
        m = _make_machine("M1")
        line.add_machine(m)
        p_a = _make_product("P-A")
        # P-A not added as compatible
        with self.assertRaises(ValueError):
            line.get_effective_capacity(p_a)


# ====================================================================== #
# 6. Maintenance listing
# ====================================================================== #

class TestMaintenanceListing(unittest.TestCase):
    """Tests for get_machines_needing_maintenance."""

    def test_one_machine_needs_maintenance(self) -> None:
        line = ProductionLine("L1", "Test")
        m1 = _make_machine("M1", maintenance_interval_hours=200,
                           operating_hours_since_maintenance=50)
        m2 = _make_machine("M2", maintenance_interval_hours=200,
                           operating_hours_since_maintenance=205)
        line.add_machine(m1)
        line.add_machine(m2)
        needing = line.get_machines_needing_maintenance()
        self.assertEqual(len(needing), 1)
        self.assertEqual(needing[0].machine_id, "M2")

    def test_no_machines_need_maintenance(self) -> None:
        line = ProductionLine("L1", "Test")
        m = _make_machine("M1", maintenance_interval_hours=200,
                          operating_hours_since_maintenance=50)
        line.add_machine(m)
        needing = line.get_machines_needing_maintenance()
        self.assertEqual(len(needing), 0)


# ====================================================================== #
# 7. Serialization (to_dict / from_dict)
# ====================================================================== #

class TestProductionLineSerialization(unittest.TestCase):
    """Tests for to_dict and from_dict."""

    def _build_line(self) -> tuple[ProductionLine, list[Machine]]:
        """Build a line with two machines for testing."""
        m1 = _make_machine("M1")
        m2 = _make_machine("M2")
        line = ProductionLine("L1", "Machining Line")
        line.add_machine(m1)
        line.add_machine(m2)
        p_a = _make_product("P-A")
        p_b = _make_product("P-B", "Shaft", 45)
        line.add_compatible_product(p_a)
        line.add_compatible_product(p_b)
        return line, [m1, m2]

    def test_to_dict_keys(self) -> None:
        """to_dict must have exactly the contract keys."""
        line, _ = self._build_line()
        d = line.to_dict()
        expected_keys = {"line_id", "name", "machine_ids", "compatible_product_codes"}
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values(self) -> None:
        line, _ = self._build_line()
        d = line.to_dict()
        self.assertEqual(d["line_id"], "L1")
        self.assertEqual(d["name"], "Machining Line")
        self.assertEqual(d["machine_ids"], ["M1", "M2"])
        self.assertEqual(d["compatible_product_codes"], ["P-A", "P-B"])  # sorted

    def test_compatible_product_codes_sorted(self) -> None:
        line = ProductionLine("L1", "Test")
        p_c = _make_product("P-C", "Housing", 60, 3)
        p_a = _make_product("P-A")
        line.add_compatible_product(p_c)
        line.add_compatible_product(p_a)
        d = line.to_dict()
        self.assertEqual(d["compatible_product_codes"], ["P-A", "P-C"])

    def test_from_dict_round_trip(self) -> None:
        line, machines = self._build_line()
        d = line.to_dict()
        machines_by_id = {m.machine_id: _make_machine(m.machine_id) for m in machines}
        restored = ProductionLine.from_dict(d, machines_by_id)
        self.assertEqual(restored.to_dict(), d)

    def test_from_dict_missing_field_raises(self) -> None:
        data = {"line_id": "L1", "name": "Test"}  # missing machine_ids, compatible_product_codes
        with self.assertRaises(ValueError) as ctx:
            ProductionLine.from_dict(data, {})
        self.assertIn("Eksik alan", str(ctx.exception))

    def test_from_dict_missing_machine_raises(self) -> None:
        data = {
            "line_id": "L1",
            "name": "Test",
            "machine_ids": ["M99"],
            "compatible_product_codes": [],
        }
        with self.assertRaises(ValueError) as ctx:
            ProductionLine.from_dict(data, {})
        self.assertIn("M99", str(ctx.exception))


# ====================================================================== #
# 8. find_lines_for_product
# ====================================================================== #

class TestFindLinesForProduct(unittest.TestCase):
    """Tests for the module-level find_lines_for_product function."""

    def _build_lines(self) -> tuple[list[ProductionLine], list[Product]]:
        p_a = _make_product("P-A")
        p_b = _make_product("P-B", "Shaft", 45, 2)
        p_c = _make_product("P-C", "Housing", 60, 3)

        l1 = ProductionLine("L1", "Machining Line")
        l1.add_machine(_make_machine("M1"))
        l1.add_compatible_product(p_a)
        l1.add_compatible_product(p_b)

        l2 = ProductionLine("L2", "Milling Line")
        l2.add_machine(_make_machine("M2"))
        l2.add_compatible_product(p_b)
        l2.add_compatible_product(p_c)

        l3 = ProductionLine("L3", "Assembly Line")
        l3.add_machine(_make_machine("M3"))
        l3.add_compatible_product(p_a)
        l3.add_compatible_product(p_c)

        return [l1, l2, l3], [p_a, p_b, p_c]

    def test_find_lines_p_a(self) -> None:
        lines, products = self._build_lines()
        result = find_lines_for_product(products[0], lines)
        ids = [ln.line_id for ln in result]
        self.assertEqual(ids, ["L1", "L3"])

    def test_find_lines_p_b(self) -> None:
        lines, products = self._build_lines()
        result = find_lines_for_product(products[1], lines)
        ids = [ln.line_id for ln in result]
        self.assertEqual(ids, ["L1", "L2"])

    def test_find_lines_p_c(self) -> None:
        lines, products = self._build_lines()
        result = find_lines_for_product(products[2], lines)
        ids = [ln.line_id for ln in result]
        self.assertEqual(ids, ["L2", "L3"])

    def test_find_lines_no_match(self) -> None:
        lines, _ = self._build_lines()
        p_x = _make_product("P-X", "Unknown", 10, 5)
        result = find_lines_for_product(p_x, lines)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
