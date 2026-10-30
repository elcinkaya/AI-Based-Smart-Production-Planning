"""
test_record.py – Unit tests for Shift and ProductionRecord.

Tests validity, boundary conditions, error handling, key extraction,
and dictionary serialization/deserialization.

Author: Kişi A
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
import unittest

from production_records.record import SHIFT_HOURS, Shift, ProductionRecord


class TestProductionRecord(unittest.TestCase):
    """Test suite for ProductionRecord model and validation."""

    def setUp(self) -> None:
        """Create valid sample data for testing."""
        self.valid_data = {
            "record_id": 1,
            "production_date": "2026-10-01",
            "shift": "morning",
            "machine_id": "M1",
            "product_code": "P-A",
            "planned_units": 800,
            "actual_units": 780,
            "downtime_hours": 0.5,
        }

    def test_constants_and_enum(self) -> None:
        """Test SHIFT_HOURS constant and Shift enum values."""
        self.assertEqual(SHIFT_HOURS, 8.0)
        self.assertEqual(Shift.MORNING.value, "morning")
        self.assertEqual(Shift.AFTERNOON.value, "afternoon")
        self.assertEqual(Shift.NIGHT.value, "night")

    def test_valid_record_creation(self) -> None:
        """Test instantiating ProductionRecord with valid arguments."""
        rec = ProductionRecord(
            production_date="2026-10-01",
            shift="morning",
            machine_id="M1",
            product_code="P-A",
            planned_units=800,
            actual_units=780,
            downtime_hours=0.5,
            record_id=1,
        )
        self.assertEqual(rec.record_id, 1)
        self.assertEqual(rec.production_date, datetime.date(2026, 10, 1))
        self.assertEqual(rec.shift, Shift.MORNING)
        self.assertEqual(rec.machine_id, "M1")
        self.assertEqual(rec.product_code, "P-A")
        self.assertEqual(rec.planned_units, 800)
        self.assertEqual(rec.actual_units, 780)
        self.assertEqual(rec.downtime_hours, 0.5)

    def test_valid_record_with_date_object_and_enum(self) -> None:
        """Test instantiating with datetime.date and Shift enum directly."""
        rec = ProductionRecord(
            production_date=datetime.date(2026, 10, 2),
            shift=Shift.AFTERNOON,
            machine_id="M2",
            product_code="P-B",
            planned_units=500,
            actual_units=500,
            downtime_hours=0.0,
            record_id=None,
        )
        self.assertIsNone(rec.record_id)
        self.assertEqual(rec.production_date, datetime.date(2026, 10, 2))
        self.assertEqual(rec.shift, Shift.AFTERNOON)
        self.assertEqual(rec.downtime_hours, 0.0)

    def test_invalid_dates(self) -> None:
        """Test rejection of malformed or invalid calendar dates."""
        invalid_dates = [
            "2026-13-40",
            "01.10.2026",
            "2026/10/01",
            "not-a-date",
            "",
            12345,
        ]
        for bad_date in invalid_dates:
            with self.subTest(bad_date=bad_date):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date=bad_date,
                        shift="morning",
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=100,
                        actual_units=100,
                    )

    def test_invalid_shifts(self) -> None:
        """Test rejection of invalid shift names or types."""
        invalid_shifts = ["evening", "midday", "", 123, None]
        for bad_shift in invalid_shifts:
            with self.subTest(bad_shift=bad_shift):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift=bad_shift,
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=100,
                        actual_units=100,
                    )

    def test_invalid_machine_and_product_ids(self) -> None:
        """Test rejection of empty machine_id or product_code."""
        for empty_val in ["", "   ", None]:
            with self.subTest(machine_id=empty_val):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id=empty_val,
                        product_code="P-A",
                        planned_units=100,
                        actual_units=100,
                    )
            with self.subTest(product_code=empty_val):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id="M1",
                        product_code=empty_val,
                        planned_units=100,
                        actual_units=100,
                    )

    def test_invalid_planned_units(self) -> None:
        """Test rejection of planned_units <= 0, floats, or bools."""
        invalid_planned = [0, -10, 800.5, 800.0, True, False, "800"]
        for bad_val in invalid_planned:
            with self.subTest(planned_units=bad_val):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=bad_val,
                        actual_units=100,
                    )

    def test_invalid_actual_units(self) -> None:
        """Test rejection of actual_units < 0, floats, or bools."""
        invalid_actual = [-1, -50, 780.5, 780.0, True, False, "780"]
        for bad_val in invalid_actual:
            with self.subTest(actual_units=bad_val):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=100,
                        actual_units=bad_val,
                    )

    def test_invalid_downtime_hours(self) -> None:
        """Test rejection of downtime_hours < 0, > 8, or bool."""
        invalid_downtime = [-0.1, -1.0, 8.1, 10.0, True, False, "0.5"]
        for bad_val in invalid_downtime:
            with self.subTest(downtime_hours=bad_val):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=100,
                        actual_units=100,
                        downtime_hours=bad_val,
                    )

    def test_invalid_record_id(self) -> None:
        """Test rejection of record_id < 1, float, or bool."""
        invalid_ids = [0, -1, 1.5, True, False, "1"]
        for bad_id in invalid_ids:
            with self.subTest(record_id=bad_id):
                with self.assertRaises((ValueError, TypeError)):
                    ProductionRecord(
                        production_date="2026-10-01",
                        shift="morning",
                        machine_id="M1",
                        product_code="P-A",
                        planned_units=100,
                        actual_units=100,
                        record_id=bad_id,
                    )

    def test_get_key(self) -> None:
        """Test that get_key returns (ISO date, shift value, machine_id)."""
        rec = ProductionRecord(
            production_date="2026-10-01",
            shift="morning",
            machine_id="M1",
            product_code="P-A",
            planned_units=800,
            actual_units=780,
            downtime_hours=0.5,
        )
        self.assertEqual(rec.get_key(), ("2026-10-01", "morning", "M1"))

    def test_to_dict(self) -> None:
        """Test dictionary serialization against the contract."""
        rec = ProductionRecord.from_dict(self.valid_data)
        d = rec.to_dict()
        self.assertEqual(d, self.valid_data)

    def test_from_dict_and_roundtrip(self) -> None:
        """Test from_dict reconstruction and roundtrip equality."""
        rec = ProductionRecord.from_dict(self.valid_data)
        self.assertEqual(rec.record_id, 1)
        self.assertEqual(rec.production_date.isoformat(), "2026-10-01")
        self.assertEqual(rec.shift, Shift.MORNING)
        self.assertEqual(rec.machine_id, "M1")
        self.assertEqual(rec.product_code, "P-A")
        self.assertEqual(rec.planned_units, 800)
        self.assertEqual(rec.actual_units, 780)
        self.assertEqual(rec.downtime_hours, 0.5)

        reconstructed = ProductionRecord.from_dict(rec.to_dict())
        self.assertEqual(rec, reconstructed)

    def test_from_dict_missing_fields(self) -> None:
        """Test from_dict raises ValueError when required fields are missing."""
        required_fields = [
            "production_date",
            "shift",
            "machine_id",
            "product_code",
            "planned_units",
            "actual_units",
            "downtime_hours",
        ]
        for field in required_fields:
            data = dict(self.valid_data)
            del data[field]
            with self.subTest(missing_field=field):
                with self.assertRaises(ValueError):
                    ProductionRecord.from_dict(data)

    def test_equality_and_repr(self) -> None:
        """Test __eq__ and __repr__ behaviors."""
        rec1 = ProductionRecord.from_dict(self.valid_data)
        rec2 = ProductionRecord.from_dict(self.valid_data)
        rec3 = ProductionRecord(
            production_date="2026-10-01",
            shift="morning",
            machine_id="M1",
            product_code="P-A",
            planned_units=800,
            actual_units=750,  # different
            downtime_hours=0.5,
            record_id=1,
        )

        self.assertEqual(rec1, rec2)
        self.assertNotEqual(rec1, rec3)
        self.assertNotEqual(rec1, "not-a-record")
        self.assertIn("ProductionRecord", repr(rec1))
        self.assertIn("M1", repr(rec1))


if __name__ == "__main__":
    unittest.main()
