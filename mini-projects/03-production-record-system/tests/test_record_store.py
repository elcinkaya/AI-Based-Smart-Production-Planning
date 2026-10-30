"""
test_record_store.py – Unit tests for the RecordStore class.

Tests cover record addition (single and batch), duplicate prevention,
valid machine/product code enforcement, ID assignment, filtering and
data persistence across file close/reopen cycles.

All file operations use tempfile.TemporaryDirectory() so that real data
files are never modified.

Author: Kişi B
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
import os
import tempfile
import unittest

from production_records.record import ProductionRecord, Shift
from production_records.record_store import RecordStore
from production_records.storage import load_records_json, load_records_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_MACHINES = {"M1", "M2", "M3", "M5"}
VALID_PRODUCTS = {"P-A", "P-B", "P-C"}


def _new_record(**overrides) -> ProductionRecord:
    """Create a ProductionRecord (record_id=None) with sensible defaults."""
    defaults = {
        "production_date": "2026-10-01",
        "shift": "morning",
        "machine_id": "M1",
        "product_code": "P-A",
        "planned_units": 800,
        "actual_units": 780,
        "downtime_hours": 0.5,
        "record_id": None,
    }
    defaults.update(overrides)
    return ProductionRecord(**defaults)


# ===========================================================================
# RecordStore construction tests
# ===========================================================================

class TestRecordStoreInit(unittest.TestCase):
    """Tests for RecordStore.__init__."""

    def test_csv_extension_accepted(self):
        """Should accept .csv extension."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "recs.csv"))
            self.assertIsNotNone(store)

    def test_json_extension_accepted(self):
        """Should accept .json extension."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "recs.json"))
            self.assertIsNotNone(store)

    def test_unsupported_extension_raises(self):
        """Unsupported extension should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                RecordStore(os.path.join(tmp, "recs.xml"))
            self.assertIn("Desteklenmeyen", str(ctx.exception))

    def test_valid_sets_stored(self):
        """Valid machine/product sets should be stored."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(
                os.path.join(tmp, "r.csv"),
                valid_machine_ids=VALID_MACHINES,
                valid_product_codes=VALID_PRODUCTS,
            )
            self.assertEqual(store.valid_machine_ids, VALID_MACHINES)
            self.assertEqual(store.valid_product_codes, VALID_PRODUCTS)


# ===========================================================================
# add_record tests
# ===========================================================================

class TestAddRecord(unittest.TestCase):
    """Tests for RecordStore.add_record."""

    def test_add_single_assigns_id_1(self):
        """First record should be assigned record_id=1."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            rec = _new_record()
            result = store.add_record(rec)
            self.assertEqual(result.record_id, 1)

    def test_add_multiple_increments_id(self):
        """Sequential adds should increment record_id."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            r1 = store.add_record(_new_record())
            r2 = store.add_record(_new_record(
                production_date="2026-10-02",
                machine_id="M2",
                product_code="P-B",
            ))
            self.assertEqual(r1.record_id, 1)
            self.assertEqual(r2.record_id, 2)

    def test_add_persists_to_file(self):
        """Added records should be readable from the file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            store = RecordStore(path)
            store.add_record(_new_record())
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 1)

    def test_non_record_raises_type_error(self):
        """Adding a non-ProductionRecord should raise TypeError."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            with self.assertRaises(TypeError):
                store.add_record({"not": "a record"})

    def test_record_with_id_raises(self):
        """Adding a record with record_id already set should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            rec = _new_record()
            rec.record_id = 5
            with self.assertRaises(ValueError) as ctx:
                store.add_record(rec)
            self.assertIn("None olmalıdır", str(ctx.exception))

    def test_duplicate_key_raises(self):
        """Adding a record with the same (date, shift, machine_id) should raise."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            store.add_record(_new_record())
            with self.assertRaises(ValueError) as ctx:
                store.add_record(_new_record())
            self.assertIn("Mükerrer", str(ctx.exception))

    def test_invalid_machine_id_raises(self):
        """Invalid machine_id should raise ValueError when valid set is provided."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(
                os.path.join(tmp, "r.json"),
                valid_machine_ids=VALID_MACHINES,
            )
            with self.assertRaises(ValueError) as ctx:
                store.add_record(_new_record(machine_id="M99"))
            self.assertIn("Geçersiz makine", str(ctx.exception))

    def test_invalid_product_code_raises(self):
        """Invalid product_code should raise ValueError when valid set is provided."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(
                os.path.join(tmp, "r.json"),
                valid_product_codes=VALID_PRODUCTS,
            )
            with self.assertRaises(ValueError) as ctx:
                store.add_record(_new_record(product_code="P-Z"))
            self.assertIn("Geçersiz ürün", str(ctx.exception))

    def test_csv_add_record(self):
        """add_record should work with CSV format as well."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.csv")
            store = RecordStore(path)
            result = store.add_record(_new_record())
            self.assertEqual(result.record_id, 1)
            loaded = load_records_csv(path)
            self.assertEqual(len(loaded), 1)


# ===========================================================================
# add_records (batch) tests
# ===========================================================================

class TestAddRecords(unittest.TestCase):
    """Tests for RecordStore.add_records (batch)."""

    def test_batch_add_assigns_sequential_ids(self):
        """Batch add should assign sequential IDs starting from 1."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            records = [
                _new_record(),
                _new_record(production_date="2026-10-02"),
                _new_record(production_date="2026-10-03"),
            ]
            result = store.add_records(records)
            self.assertEqual([r.record_id for r in result], [1, 2, 3])

    def test_batch_validates_all_first(self):
        """If any record in the batch is invalid, NONE should be written."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            store = RecordStore(path, valid_machine_ids=VALID_MACHINES)
            records = [
                _new_record(),
                _new_record(production_date="2026-10-02", machine_id="M99"),
            ]
            with self.assertRaises(ValueError):
                store.add_records(records)
            # File should remain empty / non-existent
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 0)

    def test_batch_detects_intra_batch_duplicates(self):
        """Two records within the same batch having the same key should fail."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            records = [_new_record(), _new_record()]
            with self.assertRaises(ValueError) as ctx:
                store.add_records(records)
            self.assertIn("Mükerrer", str(ctx.exception))

    def test_batch_continues_id_sequence(self):
        """Batch add after existing records should continue ID sequence."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            store.add_record(_new_record())
            batch = [
                _new_record(production_date="2026-10-02"),
                _new_record(production_date="2026-10-03"),
            ]
            result = store.add_records(batch)
            self.assertEqual([r.record_id for r in result], [2, 3])

    def test_empty_batch_is_no_op(self):
        """Empty batch should return empty list without error."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            result = store.add_records([])
            self.assertEqual(result, [])


# ===========================================================================
# get_all / get_record / count tests
# ===========================================================================

class TestGetAndCount(unittest.TestCase):
    """Tests for get_all, get_record and count."""

    def test_get_all_empty(self):
        """get_all on empty store should return empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            self.assertEqual(store.get_all(), [])

    def test_get_all_returns_records(self):
        """get_all should return all added records."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            store.add_record(_new_record())
            store.add_record(_new_record(
                production_date="2026-10-02",
                machine_id="M2",
                product_code="P-B",
            ))
            self.assertEqual(len(store.get_all()), 2)

    def test_get_record_found(self):
        """get_record should return the correct record by ID."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            store.add_record(_new_record())
            rec = store.get_record(1)
            self.assertEqual(rec.machine_id, "M1")

    def test_get_record_not_found(self):
        """get_record with nonexistent ID should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.json"))
            with self.assertRaises(ValueError) as ctx:
                store.get_record(999)
            self.assertIn("Kayıt bulunamadı", str(ctx.exception))

    def test_count(self):
        """count should return the number of records."""
        with tempfile.TemporaryDirectory() as tmp:
            store = RecordStore(os.path.join(tmp, "r.csv"))
            self.assertEqual(store.count(), 0)
            store.add_record(_new_record())
            self.assertEqual(store.count(), 1)


# ===========================================================================
# filter_records tests
# ===========================================================================

class TestFilterRecords(unittest.TestCase):
    """Tests for RecordStore.filter_records."""

    def _build_store(self, tmp: str) -> RecordStore:
        """Create a store with 3 records for filtering tests."""
        store = RecordStore(os.path.join(tmp, "r.json"))
        store.add_record(_new_record(
            production_date="2026-10-01", shift="morning",
            machine_id="M1", product_code="P-A",
        ))
        store.add_record(_new_record(
            production_date="2026-10-02", shift="afternoon",
            machine_id="M2", product_code="P-B",
        ))
        store.add_record(_new_record(
            production_date="2026-10-03", shift="morning",
            machine_id="M1", product_code="P-C",
        ))
        return store

    def test_filter_by_machine_id(self):
        """Filter by machine_id should return matching records."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(machine_id="M1")
            self.assertEqual(len(result), 2)

    def test_filter_by_date_range(self):
        """Filter by date_from and date_to should return inclusive range."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(
                date_from="2026-10-01", date_to="2026-10-02",
            )
            self.assertEqual(len(result), 2)

    def test_filter_by_shift(self):
        """Filter by shift should return matching records."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(shift="afternoon")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].machine_id, "M2")

    def test_filter_by_shift_enum(self):
        """Filter by Shift enum should work the same as string."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(shift=Shift.MORNING)
            self.assertEqual(len(result), 2)

    def test_filter_by_product_code(self):
        """Filter by product_code should return matching records."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(product_code="P-A")
            self.assertEqual(len(result), 1)

    def test_filter_combined_and(self):
        """Multiple filters should combine with AND logic."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(
                machine_id="M1", shift="morning",
            )
            self.assertEqual(len(result), 2)
            result = store.filter_records(
                machine_id="M1", product_code="P-A",
            )
            self.assertEqual(len(result), 1)

    def test_filter_no_match(self):
        """Filters with no matching records should return empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(machine_id="M99")
            self.assertEqual(result, [])

    def test_filter_by_date_from_with_date_object(self):
        """date_from as datetime.date should work correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._build_store(tmp)
            result = store.filter_records(
                date_from=datetime.date(2026, 10, 2),
            )
            self.assertEqual(len(result), 2)


# ===========================================================================
# Persistence / cross-format tests
# ===========================================================================

class TestPersistence(unittest.TestCase):
    """Tests verifying data persistence across store re-creation."""

    def test_json_store_survives_restart(self):
        """Records should persist when RecordStore is re-created (JSON)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "persist.json")
            store1 = RecordStore(path)
            store1.add_record(_new_record())
            store1.add_record(_new_record(
                production_date="2026-10-02",
                machine_id="M2",
                product_code="P-B",
            ))
            # Simulate restart
            store2 = RecordStore(path)
            self.assertEqual(store2.count(), 2)
            all_recs = store2.get_all()
            self.assertEqual(all_recs[0].record_id, 1)
            self.assertEqual(all_recs[1].record_id, 2)

    def test_csv_store_survives_restart(self):
        """Records should persist when RecordStore is re-created (CSV)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "persist.csv")
            store1 = RecordStore(path)
            store1.add_record(_new_record())
            store1.add_record(_new_record(
                production_date="2026-10-02",
                machine_id="M2",
                product_code="P-B",
            ))
            store2 = RecordStore(path)
            self.assertEqual(store2.count(), 2)

    def test_new_id_continues_after_restart(self):
        """Record IDs should continue from max after store restart."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "id_cont.json")
            store1 = RecordStore(path)
            store1.add_record(_new_record())
            store2 = RecordStore(path)
            r2 = store2.add_record(_new_record(
                production_date="2026-10-02",
                machine_id="M2",
                product_code="P-B",
            ))
            self.assertEqual(r2.record_id, 2)


# ===========================================================================
# Corrupt file tests
# ===========================================================================

class TestCorruptFile(unittest.TestCase):
    """Tests for handling corrupt files through RecordStore."""

    def test_corrupt_json_raises_on_get_all(self):
        """Corrupt JSON should raise ValueError through get_all."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "corrupt.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{corrupt data")
            store = RecordStore(path)
            with self.assertRaises(ValueError):
                store.get_all()

    def test_corrupt_csv_header_raises(self):
        """CSV with wrong header should raise ValueError through get_all."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "corrupt.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("wrong,header\n")
            store = RecordStore(path)
            with self.assertRaises(ValueError):
                store.get_all()

    def test_corrupt_file_not_modified(self):
        """Corrupt file should not be changed by failed read."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "immutable.json")
            corrupt_content = "{bad json data"
            with open(path, "w", encoding="utf-8") as f:
                f.write(corrupt_content)
            store = RecordStore(path)
            try:
                store.get_all()
            except ValueError:
                pass
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), corrupt_content)


if __name__ == "__main__":
    unittest.main()
