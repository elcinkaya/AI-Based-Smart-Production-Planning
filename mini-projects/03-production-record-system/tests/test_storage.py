"""
test_storage.py – Unit tests for the storage module (CSV/JSON I/O).

All file operations use tempfile.TemporaryDirectory() so that real data
files are never modified.

Author: Kişi B
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest

from production_records.record import ProductionRecord, Shift
from production_records.storage import (
    CSV_COLUMNS,
    JSON_SCHEMA_VERSION,
    load_records_json,
    save_records_json,
    append_record_json,
    load_records_csv,
    save_records_csv,
    append_record_csv,
    convert_records_file,
)


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _make_record(**overrides) -> ProductionRecord:
    """Create a ProductionRecord with sensible defaults and optional overrides."""
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


def _make_test_records() -> list[ProductionRecord]:
    """Return the 8 fixed test records from data/test_records.*."""
    data = [
        {"record_id": 1, "production_date": "2026-10-01", "shift": "morning",
         "machine_id": "M1", "product_code": "P-A", "planned_units": 800,
         "actual_units": 780, "downtime_hours": 0.5},
        {"record_id": 2, "production_date": "2026-10-02", "shift": "morning",
         "machine_id": "M1", "product_code": "P-B", "planned_units": 800,
         "actual_units": 760, "downtime_hours": 1.0},
        {"record_id": 3, "production_date": "2026-10-03", "shift": "morning",
         "machine_id": "M1", "product_code": "P-A", "planned_units": 800,
         "actual_units": 756, "downtime_hours": 1.0},
        {"record_id": 4, "production_date": "2026-10-01", "shift": "morning",
         "machine_id": "M2", "product_code": "P-A", "planned_units": 565,
         "actual_units": 560, "downtime_hours": 0.5},
        {"record_id": 5, "production_date": "2026-10-01", "shift": "afternoon",
         "machine_id": "M2", "product_code": "P-B", "planned_units": 565,
         "actual_units": 560, "downtime_hours": 0.5},
        {"record_id": 6, "production_date": "2026-10-01", "shift": "morning",
         "machine_id": "M3", "product_code": "P-B", "planned_units": 330,
         "actual_units": 320, "downtime_hours": 0.5},
        {"record_id": 7, "production_date": "2026-10-02", "shift": "morning",
         "machine_id": "M3", "product_code": "P-C", "planned_units": 330,
         "actual_units": 320, "downtime_hours": 0.5},
        {"record_id": 8, "production_date": "2026-10-03", "shift": "morning",
         "machine_id": "M3", "product_code": "P-B", "planned_units": 320,
         "actual_units": 310, "downtime_hours": 0.5},
    ]
    return [ProductionRecord.from_dict(d) for d in data]


# ===========================================================================
# JSON Tests
# ===========================================================================

class TestLoadRecordsJson(unittest.TestCase):
    """Tests for load_records_json."""

    def test_missing_file_returns_empty(self):
        """Missing file should return an empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            result = load_records_json(os.path.join(tmp, "no_such.json"))
            self.assertEqual(result, [])

    def test_empty_file_returns_empty(self):
        """A zero-byte file should return an empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.json")
            open(path, "w").close()
            result = load_records_json(path)
            self.assertEqual(result, [])

    def test_load_valid_records(self):
        """Should correctly parse valid JSON records."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "recs.json")
            save_records_json(path, records)
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 8)
            self.assertEqual(loaded[0].machine_id, "M1")
            self.assertEqual(loaded[0].record_id, 1)

    def test_invalid_json_raises(self):
        """Corrupt JSON content should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{invalid json content")
            with self.assertRaises(ValueError) as ctx:
                load_records_json(path)
            self.assertIn("geçersiz JSON", str(ctx.exception))

    def test_missing_records_key_raises(self):
        """JSON without 'records' key should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad_schema.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 1, "data": []}, f)
            with self.assertRaises(ValueError) as ctx:
                load_records_json(path)
            self.assertIn("'records' anahtarı", str(ctx.exception))


class TestSaveRecordsJson(unittest.TestCase):
    """Tests for save_records_json."""

    def test_save_creates_file(self):
        """File should be created and contain valid JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            rec = _make_record(record_id=1)
            save_records_json(path, [rec])
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["schema_version"], JSON_SCHEMA_VERSION)
            self.assertEqual(len(data["records"]), 1)

    def test_atomic_write_no_tmp_left(self):
        """Temp file should be cleaned up after successful write."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "atomic.json")
            save_records_json(path, [_make_record(record_id=1)])
            self.assertFalse(os.path.exists(path + ".tmp"))

    def test_save_creates_subdirectories(self):
        """Parent directories should be created if missing."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "dir", "recs.json")
            save_records_json(path, [])
            self.assertTrue(os.path.exists(path))

    def test_save_overwrites_existing(self):
        """Re-saving should overwrite all previous content."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "over.json")
            save_records_json(path, _make_test_records())
            save_records_json(path, [_make_record(record_id=99)])
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].record_id, 99)

    def test_type_error_on_non_record(self):
        """Non-ProductionRecord elements should raise TypeError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with self.assertRaises(TypeError):
                save_records_json(path, [{"not": "a record"}])


class TestAppendRecordJson(unittest.TestCase):
    """Tests for append_record_json."""

    def test_append_creates_file(self):
        """Appending to a nonexistent file should create it."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new.json")
            rec = _make_record(record_id=1)
            append_record_json(path, rec)
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 1)

    def test_append_preserves_existing(self):
        """Existing records must not be lost after an append."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "grow.json")
            r1 = _make_record(record_id=1)
            save_records_json(path, [r1])
            r2 = _make_record(
                record_id=2, production_date="2026-10-02",
                machine_id="M2", product_code="P-B",
            )
            append_record_json(path, r2)
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].record_id, 1)
            self.assertEqual(loaded[1].record_id, 2)


# ===========================================================================
# CSV Tests
# ===========================================================================

class TestLoadRecordsCsv(unittest.TestCase):
    """Tests for load_records_csv."""

    def test_missing_file_returns_empty(self):
        """Missing file should return an empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            result = load_records_csv(os.path.join(tmp, "no.csv"))
            self.assertEqual(result, [])

    def test_empty_file_returns_empty(self):
        """A zero-byte file should return an empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.csv")
            open(path, "w").close()
            result = load_records_csv(path)
            self.assertEqual(result, [])

    def test_load_valid_csv(self):
        """Should correctly parse valid CSV records."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "recs.csv")
            save_records_csv(path, records)
            loaded = load_records_csv(path)
            self.assertEqual(len(loaded), 8)
            self.assertEqual(loaded[0].planned_units, 800)

    def test_wrong_header_raises(self):
        """Incorrect header should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad_hdr.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("wrong,header,line\n")
            with self.assertRaises(ValueError) as ctx:
                load_records_csv(path)
            self.assertIn("başlık satırı", str(ctx.exception))

    def test_invalid_data_in_row_raises(self):
        """Non-numeric value in a numeric column should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad_data.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(",".join(CSV_COLUMNS) + "\n")
                f.write("1,2026-10-01,morning,M1,P-A,abc,780,0.5\n")
            with self.assertRaises(ValueError) as ctx:
                load_records_csv(path)
            self.assertIn("satır", str(ctx.exception))


class TestSaveRecordsCsv(unittest.TestCase):
    """Tests for save_records_csv."""

    def test_save_creates_file_with_header(self):
        """CSV file should have the correct header."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            save_records_csv(path, [_make_record(record_id=1)])
            with open(path, encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
            self.assertEqual(header, CSV_COLUMNS)

    def test_empty_save_writes_header_only(self):
        """Saving an empty list should still write the header."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "hdr.csv")
            save_records_csv(path, [])
            with open(path, encoding="utf-8", newline="") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)


class TestAppendRecordCsv(unittest.TestCase):
    """Tests for append_record_csv."""

    def test_append_creates_file_with_header(self):
        """Appending to a new file should write header + record."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new.csv")
            rec = _make_record(record_id=1)
            append_record_csv(path, rec)
            loaded = load_records_csv(path)
            self.assertEqual(len(loaded), 1)

    def test_append_preserves_existing_rows(self):
        """Existing rows must remain intact after an append."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "grow.csv")
            r1 = _make_record(record_id=1)
            save_records_csv(path, [r1])
            r2 = _make_record(
                record_id=2, production_date="2026-10-02",
                machine_id="M2", product_code="P-B",
            )
            append_record_csv(path, r2)
            loaded = load_records_csv(path)
            self.assertEqual(len(loaded), 2)

    def test_append_does_not_duplicate_header(self):
        """Header must not be duplicated when appending to existing file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no_dup.csv")
            save_records_csv(path, [_make_record(record_id=1)])
            append_record_csv(
                path,
                _make_record(record_id=2, production_date="2026-10-02"),
            )
            with open(path, encoding="utf-8", newline="") as f:
                content = f.read()
            header_line = ",".join(CSV_COLUMNS)
            self.assertEqual(content.count(header_line), 1)


# ===========================================================================
# Conversion Tests
# ===========================================================================

class TestConvertRecordsFile(unittest.TestCase):
    """Tests for convert_records_file."""

    def test_json_to_csv(self):
        """JSON -> CSV conversion should preserve all records."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src.json")
            tgt = os.path.join(tmp, "tgt.csv")
            save_records_json(src, records)
            count = convert_records_file(src, tgt)
            self.assertEqual(count, 8)
            loaded = load_records_csv(tgt)
            self.assertEqual(len(loaded), 8)

    def test_csv_to_json(self):
        """CSV -> JSON conversion should preserve all records."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src.csv")
            tgt = os.path.join(tmp, "tgt.json")
            save_records_csv(src, records)
            count = convert_records_file(src, tgt)
            self.assertEqual(count, 8)
            loaded = load_records_json(tgt)
            self.assertEqual(len(loaded), 8)

    def test_roundtrip_csv_json_csv(self):
        """CSV -> JSON -> CSV roundtrip should yield identical records."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            csv1 = os.path.join(tmp, "original.csv")
            json_mid = os.path.join(tmp, "mid.json")
            csv2 = os.path.join(tmp, "final.csv")
            save_records_csv(csv1, records)
            convert_records_file(csv1, json_mid)
            convert_records_file(json_mid, csv2)
            original = load_records_csv(csv1)
            final = load_records_csv(csv2)
            self.assertEqual(original, final)

    def test_same_extension_raises(self):
        """Source and target with the same extension should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                convert_records_file(
                    os.path.join(tmp, "a.csv"),
                    os.path.join(tmp, "b.csv"),
                )

    def test_unsupported_extension_raises(self):
        """Unsupported extension should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                convert_records_file(
                    os.path.join(tmp, "a.xml"),
                    os.path.join(tmp, "b.csv"),
                )


# ===========================================================================
# Data persistence / integrity tests
# ===========================================================================

class TestDataPersistence(unittest.TestCase):
    """Tests verifying that data survives file close/reopen cycles."""

    def test_json_persistence(self):
        """Records written to JSON should survive file close and reopen."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "persist.json")
            save_records_json(path, records)
            # Simulate program restart: re-read from file
            loaded = load_records_json(path)
            self.assertEqual(len(loaded), 8)
            for orig, loaded_rec in zip(records, loaded):
                self.assertEqual(orig.to_dict(), loaded_rec.to_dict())

    def test_csv_persistence(self):
        """Records written to CSV should survive file close and reopen."""
        records = _make_test_records()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "persist.csv")
            save_records_csv(path, records)
            loaded = load_records_csv(path)
            self.assertEqual(len(loaded), 8)
            for orig, loaded_rec in zip(records, loaded):
                self.assertEqual(orig.to_dict(), loaded_rec.to_dict())

    def test_json_utf8_encoding(self):
        """JSON file should use UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "utf8.json")
            save_records_json(path, [_make_record(record_id=1)])
            with open(path, "rb") as f:
                raw = f.read()
            # Should be valid UTF-8 without BOM
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            raw.decode("utf-8")  # should not raise


if __name__ == "__main__":
    unittest.main()
