"""
test_serialization.py – Unit tests for JSON/CSV serialization functions.

Tests cover:
  - factory_to_dict with Product objects
  - JSON save and load round-trip (Product only, until Machine/Line are ready)
  - CSV export headers and row count
  - factory_from_dict raises RuntimeError when Machine/ProductionLine are
    not available

Author: Kişi A
Mini Project: 02 – Factory Object Model
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from factory_model.product import Product
from factory_model import serialization


# ===================================================================
# Helper – Fake Machine (stub) for CSV / dict tests
# ===================================================================

class FakeMachine:
    """Minimal Machine stub that satisfies serialization's to_dict contract.

    Used until Kişi B completes machine.py.  Exposes the same
    ``to_dict`` key set defined in the data contract (section 3.4).
    """

    def __init__(
        self,
        machine_id: str = "M1",
        name: str = "CNC Lathe 1",
        working_hours: float = 8.0,
        cycle_time_sec: float = 30.0,
        efficiency_pct: float = 85.0,
        maintenance_interval_hours: float = 200.0,
        status: str = "running",
        operating_hours_since_maintenance: float = 50.0,
        line_id: str | None = "L1",
    ) -> None:
        self.machine_id = machine_id
        self.name = name
        self.working_hours = working_hours
        self.cycle_time_sec = cycle_time_sec
        self.efficiency_pct = efficiency_pct
        self.maintenance_interval_hours = maintenance_interval_hours
        self.status = status
        self.operating_hours_since_maintenance = operating_hours_since_maintenance
        self.line_id = line_id

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "name": self.name,
            "working_hours": self.working_hours,
            "cycle_time_sec": self.cycle_time_sec,
            "efficiency_pct": self.efficiency_pct,
            "maintenance_interval_hours": self.maintenance_interval_hours,
            "status": self.status,
            "operating_hours_since_maintenance": self.operating_hours_since_maintenance,
            "line_id": self.line_id,
        }


class FakeLine:
    """Minimal ProductionLine stub for factory_to_dict tests."""

    def __init__(
        self,
        line_id: str = "L1",
        name: str = "Machining Line",
        machine_ids: list | None = None,
        compatible_product_codes: list | None = None,
    ) -> None:
        self.line_id = line_id
        self.name = name
        self._machine_ids = machine_ids or []
        self._compatible_product_codes = compatible_product_codes or []

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "name": self.name,
            "machine_ids": list(self._machine_ids),
            "compatible_product_codes": sorted(self._compatible_product_codes),
        }


# ===================================================================
# factory_to_dict tests
# ===================================================================

class TestFactoryToDict(unittest.TestCase):
    """Tests for factory_to_dict."""

    def test_products_only(self) -> None:
        products = [
            Product("P-A", "Bracket", 30.0, 1),
            Product("P-B", "Shaft", 45.0, 2),
        ]
        result = serialization.factory_to_dict(products, [], [])
        self.assertIn("products", result)
        self.assertIn("machines", result)
        self.assertIn("lines", result)
        self.assertEqual(len(result["products"]), 2)
        self.assertEqual(len(result["machines"]), 0)
        self.assertEqual(len(result["lines"]), 0)

    def test_with_stubs(self) -> None:
        products = [Product("P-A", "Bracket", 30.0, 1)]
        machines = [FakeMachine(), FakeMachine(machine_id="M2")]
        lines = [FakeLine()]
        result = serialization.factory_to_dict(products, machines, lines)
        self.assertEqual(len(result["products"]), 1)
        self.assertEqual(len(result["machines"]), 2)
        self.assertEqual(len(result["lines"]), 1)

    def test_product_dict_keys(self) -> None:
        products = [Product("P-C", "Housing", 60.0, 3)]
        result = serialization.factory_to_dict(products, [], [])
        p_dict = result["products"][0]
        self.assertEqual(
            set(p_dict.keys()),
            {"product_code", "name", "processing_time_sec", "priority"},
        )


# ===================================================================
# JSON save / load round-trip (Product-level)
# ===================================================================

class TestJsonRoundTrip(unittest.TestCase):
    """Tests for save_factory_json and load_factory_json at the Product level.

    Full round-trip (with real Machine & ProductionLine) will be tested
    after Kişi B and Kişi C complete their modules.
    """

    def setUp(self) -> None:
        self.products = [
            Product("P-A", "Bracket", 30.0, 1),
            Product("P-B", "Shaft", 45.0, 2),
            Product("P-C", "Housing", 60.0, 3),
        ]
        self.tmp_dir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.tmp_dir, "test_factory.json")

    def test_save_creates_file(self) -> None:
        serialization.save_factory_json(
            self.json_path, self.products, [], []
        )
        self.assertTrue(os.path.exists(self.json_path))

    def test_saved_json_structure(self) -> None:
        serialization.save_factory_json(
            self.json_path, self.products, [], []
        )
        with open(self.json_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("products", data)
        self.assertIn("machines", data)
        self.assertIn("lines", data)
        self.assertEqual(len(data["products"]), 3)

    def test_product_round_trip_via_json(self) -> None:
        """Save products to JSON, re-read raw JSON, reconstruct Products."""
        serialization.save_factory_json(
            self.json_path, self.products, [], []
        )
        with open(self.json_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        restored = [Product.from_dict(d) for d in raw["products"]]
        for orig, rest in zip(self.products, restored):
            self.assertEqual(orig.to_dict(), rest.to_dict())

    def test_json_encoding_utf8(self) -> None:
        """Turkish characters (if any) survive JSON encoding."""
        p = Product("P-T", "Çelik Braket", 25.0, 2)
        serialization.save_factory_json(
            self.json_path, [p], [], []
        )
        with open(self.json_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self.assertEqual(raw["products"][0]["name"], "Çelik Braket")


# ===================================================================
# CSV export tests
# ===================================================================

class TestCsvExport(unittest.TestCase):
    """Tests for export_machines_csv (using FakeMachine stubs)."""

    def setUp(self) -> None:
        self.machines = [
            FakeMachine(machine_id="M1"),
            FakeMachine(machine_id="M2", name="CNC Lathe 2", working_hours=16,
                        cycle_time_sec=45, efficiency_pct=90,
                        operating_hours_since_maintenance=205, status="idle"),
        ]
        self.tmp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.tmp_dir, "machines.csv")

    def test_csv_file_created(self) -> None:
        serialization.export_machines_csv(self.csv_path, self.machines)
        self.assertTrue(os.path.exists(self.csv_path))

    def test_csv_header(self) -> None:
        serialization.export_machines_csv(self.csv_path, self.machines)
        with open(self.csv_path, "r", encoding="utf-8") as fh:
            header = fh.readline().strip()
        expected = ",".join(serialization._MACHINE_CSV_HEADERS)
        self.assertEqual(header, expected)

    def test_csv_row_count(self) -> None:
        serialization.export_machines_csv(self.csv_path, self.machines)
        with open(self.csv_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        # 1 header + 2 data rows
        self.assertEqual(len(lines), 3)

    def test_csv_empty_list(self) -> None:
        serialization.export_machines_csv(self.csv_path, [])
        with open(self.csv_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        # Only header
        self.assertEqual(len(lines), 1)


# ===================================================================
# factory_from_dict – integration guard
# ===================================================================

class TestFactoryFromDictGuard(unittest.TestCase):
    """Verify factory_from_dict raises RuntimeError when dependencies
    are missing, and works for products."""

    def test_products_deserialize(self) -> None:
        """Products can be deserialized even without Machine/Line modules."""
        data = {
            "products": [
                {"product_code": "P-A", "name": "Bracket",
                 "processing_time_sec": 30.0, "priority": 1},
            ],
            "machines": [],
            "lines": [],
        }
        # If Machine class is available (module exists), this should work.
        # If not, machines list is empty so no RuntimeError.
        result = serialization.factory_from_dict(data)
        self.assertEqual(len(result["products"]), 1)
        self.assertIsInstance(result["products"][0], Product)

    def test_machines_without_module_raises(self) -> None:
        """If Machine module is unavailable and machine data is provided,
        RuntimeError should be raised."""
        if serialization.Machine is not None:
            self.skipTest("Machine module is available; guard not needed.")
        data = {
            "products": [],
            "machines": [{"machine_id": "M1", "name": "X"}],
            "lines": [],
        }
        with self.assertRaises(RuntimeError):
            serialization.factory_from_dict(data)


# ===================================================================
# Run
# ===================================================================

if __name__ == "__main__":
    unittest.main()
