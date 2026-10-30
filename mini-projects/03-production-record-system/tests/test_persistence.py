"""
test_persistence.py – End-to-end "close and reopen" persistence tests.

Success criterion of Mini Project 3: after the program is closed and opened
again, old records are kept and new records are appended without corrupting
them. Section 7.3 of the plan (the scenario list) is referenced but missing
from the document, so the scenarios below are derived from Sections 1, 3.1
and 3.3 and from the Kişi C task description ("by re-creating the
RecordStore object and with a separate subprocess").

Three levels are tested, for both .csv and .json:
    1. RecordStore re-created in the same process,
    2. separate Python processes (subprocess) writing and reading the file,
    3. the real menu program (main.py) run several times as a subprocess.

Every test runs inside tempfile.TemporaryDirectory(); the real data/ folder
is only READ (sample_factory.json, sample_records.json), never written.

Author: Kişi C
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from factory_model.serialization import load_factory_json
from production_records.analysis import summarize_records
from production_records.generate_records import generate_records
from production_records.record import ProductionRecord
from production_records.record_store import RecordStore
from production_records.storage import (
    convert_records_file,
    load_records_csv,
    load_records_json,
)


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
MAIN_PY = os.path.join(PROJECT_DIR, "main.py")

VALID_MACHINES = {"M1", "M2", "M3", "M4", "M5"}
VALID_PRODUCTS = {"P-A", "P-B", "P-C"}

RAW_TEST_RECORDS: list[tuple] = [
    ("2026-10-01", "morning", "M1", "P-A", 800, 780, 0.5),
    ("2026-10-02", "morning", "M1", "P-B", 800, 760, 1.0),
    ("2026-10-03", "morning", "M1", "P-A", 800, 756, 1.0),
    ("2026-10-01", "morning", "M2", "P-A", 565, 560, 0.5),
    ("2026-10-01", "afternoon", "M2", "P-B", 565, 560, 0.5),
    ("2026-10-01", "morning", "M3", "P-B", 330, 320, 0.5),
    ("2026-10-02", "morning", "M3", "P-C", 330, 320, 0.5),
    ("2026-10-03", "morning", "M3", "P-B", 320, 310, 0.5),
]

FORMATS = (".csv", ".json")


def new_test_records() -> list[ProductionRecord]:
    """Return the 8 test records without record_id (ready to be added)."""
    return [ProductionRecord(*raw) for raw in RAW_TEST_RECORDS]


def open_store(path: str) -> RecordStore:
    """Create a RecordStore the same way main.py does (with valid id sets)."""
    return RecordStore(path, VALID_MACHINES, VALID_PRODUCTS)


def load_any(path: str) -> list[ProductionRecord]:
    """Load records from a .csv or .json file."""
    return load_records_json(path) if path.endswith(".json") else load_records_csv(path)


def child_env() -> dict[str, str]:
    """Environment for child processes: UTF-8 stdio, project on sys.path."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = PROJECT_DIR
    return env


def run_python(code: str) -> subprocess.CompletedProcess:
    """Run *code* in a separate Python process (cwd = project directory)."""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_DIR, env=child_env(), capture_output=True,
        text=True, encoding="utf-8", timeout=60,
    )


def run_main(user_input: list[str]) -> subprocess.CompletedProcess:
    """Run main.py as a separate process, feeding *user_input* lines to stdin."""
    return subprocess.run(
        [sys.executable, MAIN_PY],
        input="\n".join(user_input) + "\n",
        cwd=PROJECT_DIR, env=child_env(), capture_output=True,
        text=True, encoding="utf-8", timeout=120,
    )


# ---------------------------------------------------------------------------
# 1. RecordStore re-created in the same process
# ---------------------------------------------------------------------------

class TestStoreReopen(unittest.TestCase):
    """Closing = dropping the RecordStore object; reopening = a new object."""

    def test_records_survive_reopen(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                store = open_store(path)
                store.add_records(new_test_records())
                del store

                reopened = open_store(path)
                records = reopened.get_all()
                self.assertEqual(reopened.count(), 8)
                self.assertEqual([r.record_id for r in records], list(range(1, 9)))
                expected = [ProductionRecord(*raw, record_id=i)
                            for i, raw in enumerate(RAW_TEST_RECORDS, start=1)]
                self.assertEqual(records, expected)

    def test_append_after_reopen_keeps_old_records(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                open_store(path).add_records(new_test_records())
                old_dicts = [r.to_dict() for r in load_any(path)]
                with open(path, "rb") as fh:
                    old_bytes = fh.read()

                # Session 2: add one new record
                added = open_store(path).add_record(
                    ProductionRecord("2026-10-04", "night", "M5", "P-C", 400, 410, 0.0))
                self.assertEqual(added.record_id, 9)

                # Session 3: everything is there, old records unchanged
                records = open_store(path).get_all()
                self.assertEqual(len(records), 9)
                self.assertEqual([r.to_dict() for r in records[:8]], old_dicts)
                self.assertEqual(records[8].to_dict()["machine_id"], "M5")
                if ext == ".csv":
                    # 'a' mode: the old bytes are an untouched prefix of the file
                    with open(path, "rb") as fh:
                        self.assertTrue(fh.read().startswith(old_bytes))
                else:
                    with open(path, encoding="utf-8") as fh:
                        payload = json.load(fh)
                    self.assertEqual(payload["schema_version"], 1)
                    self.assertEqual(len(payload["records"]), 9)

    def test_record_ids_continue_across_sessions(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                ids = []
                for day in ("2026-10-01", "2026-10-02", "2026-10-03"):
                    rec = open_store(path).add_record(
                        ProductionRecord(day, "morning", "M1", "P-A", 800, 790, 0.0))
                    ids.append(rec.record_id)
                self.assertEqual(ids, [1, 2, 3])
                self.assertEqual(open_store(path).count(), 3)

    def test_kpi_summary_same_after_reopen(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                store = open_store(path)
                store.add_records(new_test_records())
                before = summarize_records(store.get_all())
                del store
                after = summarize_records(open_store(path).get_all())
                self.assertEqual(after, before)
                self.assertEqual(after["production_gap"], -144)

    def test_missing_file_and_folder_created_on_first_add(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "new_folder", "records" + ext)
                store = open_store(path)
                self.assertEqual(store.get_all(), [])
                self.assertFalse(os.path.exists(path))
                store.add_record(new_test_records()[0])
                self.assertTrue(os.path.exists(path))
                self.assertEqual(open_store(path).count(), 1)

    def test_rejected_records_leave_file_intact(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                open_store(path).add_records(new_test_records())
                with open(path, "rb") as fh:
                    before = fh.read()

                store = open_store(path)
                with self.assertRaises(ValueError):      # duplicate key
                    store.add_record(ProductionRecord(*RAW_TEST_RECORDS[0]))
                with self.assertRaises(ValueError):      # unknown machine
                    store.add_record(
                        ProductionRecord("2026-10-09", "morning", "M9", "P-A", 1, 1))
                with self.assertRaises(ValueError):      # batch: nothing written
                    store.add_records([
                        ProductionRecord("2026-10-09", "morning", "M1", "P-A", 1, 1),
                        ProductionRecord(*RAW_TEST_RECORDS[1]),
                    ])

                with open(path, "rb") as fh:
                    self.assertEqual(fh.read(), before)
                self.assertEqual(open_store(path).count(), 8)

    def test_converted_file_reopens_with_same_records(self) -> None:
        for src_ext, tgt_ext in ((".csv", ".json"), (".json", ".csv")):
            with self.subTest(src=src_ext), tempfile.TemporaryDirectory() as tmp:
                source = os.path.join(tmp, "records" + src_ext)
                target = os.path.join(tmp, "records" + tgt_ext)
                open_store(source).add_records(new_test_records())
                self.assertEqual(convert_records_file(source, target), 8)

                converted = open_store(target)
                self.assertEqual(converted.get_all(), open_store(source).get_all())
                converted.add_record(
                    ProductionRecord("2026-10-04", "morning", "M1", "P-A", 800, 800))
                self.assertEqual(open_store(target).count(), 9)


# ---------------------------------------------------------------------------
# 2. Separate Python processes
# ---------------------------------------------------------------------------

WRITER_CODE = """
import sys
from production_records.record import ProductionRecord
from production_records.record_store import RecordStore
raw = {raw!r}
store = RecordStore({path!r}, {machines!r}, {products!r})
store.add_records([ProductionRecord(*r) for r in raw])
print(store.count())
"""

APPENDER_CODE = """
from production_records.record import ProductionRecord
from production_records.record_store import RecordStore
store = RecordStore({path!r}, {machines!r}, {products!r})
rec = store.add_record(ProductionRecord('2026-10-04', 'night', 'M5', 'P-C', 400, 410, 0.25))
print(rec.record_id)
"""

READER_CODE = """
import json
from production_records.analysis import summarize_records
from production_records.record_store import RecordStore
store = RecordStore({path!r})
records = store.get_all()
print(json.dumps({{"records": [r.to_dict() for r in records],
                   "summary": summarize_records(records)}}))
"""


class TestSubprocessPersistence(unittest.TestCase):
    """Data written by one process is read and extended by later processes."""

    def _run_ok(self, code: str) -> str:
        result = run_python(code)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return result.stdout.strip()

    def test_write_close_read_append_read(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                fmt = {"path": path, "machines": VALID_MACHINES,
                       "products": VALID_PRODUCTS, "raw": RAW_TEST_RECORDS}

                # Process 1 writes 8 records and exits
                self.assertEqual(self._run_ok(WRITER_CODE.format(**fmt)), "8")

                # Process 2 reads them back
                first = json.loads(self._run_ok(READER_CODE.format(**fmt)))
                expected = [ProductionRecord(*raw, record_id=i).to_dict()
                            for i, raw in enumerate(RAW_TEST_RECORDS, start=1)]
                self.assertEqual(first["records"], expected)
                self.assertEqual(first["summary"]["total_planned_units"], 4510)
                self.assertEqual(first["summary"]["total_actual_units"], 4366)

                # Process 3 appends one record
                self.assertEqual(self._run_ok(APPENDER_CODE.format(**fmt)), "9")

                # Process 4 sees old records unchanged plus the new one
                second = json.loads(self._run_ok(READER_CODE.format(**fmt)))
                self.assertEqual(second["records"][:8], expected)
                self.assertEqual(second["records"][8]["record_id"], 9)
                self.assertEqual(second["summary"]["record_count"], 9)
                self.assertEqual(second["summary"]["total_planned_units"], 4510 + 400)


# ---------------------------------------------------------------------------
# 3. The real menu program (main.py) run several times
# ---------------------------------------------------------------------------

def add_record_inputs(day: str, shift: str, machine: str, product: str,
                      planned: str, actual: str, downtime: str) -> list[str]:
    """Menu input lines for option 1 (fields in the order main.py asks them)."""
    return ["1", day, shift, machine, product, planned, actual, downtime]


class TestMainProgramPersistence(unittest.TestCase):
    """Run main.py, exit with option 7, start it again and check the data."""

    def _run_main_ok(self, user_input: list[str]) -> str:
        result = run_main(user_input)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout

    def test_close_and_reopen_keeps_and_appends_records(self) -> None:
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)

                # Session 1: new file, one record (decimal comma for downtime)
                out1 = self._run_main_ok(
                    [path]
                    + add_record_inputs("2026-10-01", "morning", "M1", "P-A",
                                        "800", "780", "0,5")
                    + ["7"])
                self.assertIn("Dosya henüz yok", out1)
                self.assertIn("Kayıt eklendi. Kayıt numarası: 1", out1)
                first = load_any(path)
                self.assertEqual(len(first), 1)
                first_dict = first[0].to_dict()

                # Session 2: the record from session 1 is still there; add another
                out2 = self._run_main_ok(
                    [path]
                    + add_record_inputs("2026-10-01", "afternoon", "M2", "P-B",
                                        "565", "560", "0.5")
                    + ["7"])
                self.assertIn("Dosyadaki mevcut kayıt sayısı: 1", out2)
                self.assertIn("Kayıt eklendi. Kayıt numarası: 2", out2)

                # Session 3: list and summarize both records
                out3 = self._run_main_ok([path, "2", "h", "3", "7"])
                self.assertIn("Dosyadaki mevcut kayıt sayısı: 2", out3)
                self.assertIn("Toplam 2 kayıt listelendi.", out3)
                self.assertIn("Planlanan üretim      : 1365 adet", out3)
                self.assertIn("Gerçekleşen üretim    : 1340 adet", out3)
                self.assertIn("Üretim açığı: 25 adet", out3)

                records = load_any(path)
                self.assertEqual([r.record_id for r in records], [1, 2])
                self.assertEqual(records[0].to_dict(), first_dict)

    def test_duplicate_entry_in_new_session_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "records.csv")
            self._run_main_ok(
                [path] + add_record_inputs("2026-10-01", "morning", "M1", "P-A",
                                           "800", "780", "0") + ["7"])
            with open(path, "rb") as fh:
                before = fh.read()
            out = self._run_main_ok([path, "1", "2026-10-01", "morning", "M1", "7"])
            self.assertIn("kaydı zaten var", out)
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), before)

    def test_generated_sample_data_persists(self) -> None:
        factory = load_factory_json(os.path.join(DATA_DIR, "sample_factory.json"))
        expected = [r.to_dict() for r in generate_records(factory, "2026-10-01", 30, 42)]
        for ext in FORMATS:
            with self.subTest(fmt=ext), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "records" + ext)
                out1 = self._run_main_ok([path, "5", "", "30", "42", "7"])
                self.assertIn("150 kayıt üretildi", out1)

                out2 = self._run_main_ok([path, "4", "1", "7"])
                self.assertIn("Dosyadaki mevcut kayıt sayısı: 150", out2)
                self.assertIn("Makine Bazında", out2)

                stored = [r.to_dict() for r in load_any(path)]
                for idx, rec in enumerate(expected, start=1):
                    rec["record_id"] = idx
                self.assertEqual(stored, expected)

                # Same seed again: every key is a duplicate, nothing is written
                out3 = self._run_main_ok([path, "5", "", "30", "42", "7"])
                self.assertIn("Hiçbir kayıt yazılmadı.", out3)
                self.assertEqual(len(load_any(path)), 150)

    def test_generated_data_matches_delivered_sample_file(self) -> None:
        # Integration check of Kişi A's delivered data/sample_records.json (read-only)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "records.json")
            self._run_main_ok([path, "5", "2026-10-01", "30", "42", "7"])
            self.assertEqual(load_records_json(path),
                             load_records_json(os.path.join(DATA_DIR, "sample_records.json")))

    def test_convert_menu_creates_readable_other_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "records.csv")
            json_path = os.path.join(tmp, "records.json")
            self._run_main_ok(
                [csv_path] + add_record_inputs("2026-10-01", "morning", "M1", "P-A",
                                               "800", "780", "0.5") + ["6", "", "", "7"])
            self.assertEqual(load_records_json(json_path), load_records_csv(csv_path))

            out = self._run_main_ok([json_path, "7"])
            self.assertIn("Dosyadaki mevcut kayıt sayısı: 1", out)

    def test_corrupt_file_is_reported_and_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.csv")
            good = os.path.join(tmp, "good.csv")
            with open(bad, "w", encoding="utf-8", newline="") as fh:
                fh.write("tarih,makine\n2026-10-01,M1\n")
            with open(bad, "rb") as fh:
                before = fh.read()

            out = self._run_main_ok([bad, good, "7"])
            self.assertIn("Hata:", out)
            self.assertIn("Lütfen başka bir dosya yolu giriniz.", out)
            with open(bad, "rb") as fh:
                self.assertEqual(fh.read(), before)

    def test_end_of_input_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._run_main_ok([os.path.join(tmp, "records.csv"), "1", "2026-10-01"])
            self.assertIn("Program kullanıcı tarafından sonlandırıldı.", out)


if __name__ == "__main__":
    unittest.main()
