"""
test_fault_injection.py - Unit tests for dataset.py and fault_injection.py (Kişi A).

Covers Section 5 (Stage 4), Section 7.2 (all golden values), Section 7.6 (#5)
and Section 7.7:
- build_clean_records(factory, days=120, seed=42) produces 600 records:
  M1: 120, M2: 240, M3: 120, M5: 120; planned_units = 322489,
  actual_units = 298071, downtime_hours = 238.0.
- write_raw_datasets writes raw_records_clean.csv (readable by MP3 RecordStore
  with 600 records and no errors), raw_records_dirty.csv/.json (610 rows) and
  fault_injection_log.csv (76 rows).
- inject_faults(clean_df, seed=42) matches all Section 7.2 golden values:
  - 610 dirty rows, 76 log rows (66 corrupted + 10 duplicates)
  - exact fault counts per FAULT_PLAN + 10 duplicate_key
  - first 5 corrupted record_ids: [250, 576, 294, 40, 491] (all missing_actual_units)
  - first 5 duplicated source record_ids: [55, 201, 261, 176, 327] -> ids 601-605
  - same seed produces identical results; clean_df is never modified.
- CSV and JSON dirty files loaded via load_records_dataframe are identical,
  have 12 <NA> in actual_units and 12 <NA> in downtime_hours, and all string
  dtypes.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import pandas as pd

from factory_model.serialization import load_factory_json
from production_analysis.dataset import build_clean_records, write_raw_datasets
from production_analysis.fault_injection import (
    DUPLICATE_COUNT,
    FAULT_PLAN,
    inject_faults,
    save_dirty_records,
)
from production_analysis.loading import load_records_dataframe, records_to_dataframe
from production_analysis.schema import RECORD_COLUMNS
from production_records.record_store import RecordStore

SAMPLE_FACTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_factory.json"


class TestDatasetAndFaultInjectionGolden(unittest.TestCase):
    """Verify Section 7.2 golden values for raw clean and dirty datasets."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(str(SAMPLE_FACTORY_PATH))
        cls.clean_records = build_clean_records(cls.factory, days=120, seed=42)
        for idx, rec in enumerate(cls.clean_records, start=1):
            rec.record_id = idx
        cls.clean_typed_df = records_to_dataframe(cls.clean_records)
        # Convert to raw string frame just as load_records_dataframe would return
        cls.clean_raw_df = pd.DataFrame(
            {
                col: (
                    cls.clean_typed_df[col].dt.strftime("%Y-%m-%d").astype("string")
                    if col == "production_date"
                    else cls.clean_typed_df[col].astype("string")
                )
                for col in RECORD_COLUMNS
            },
            columns=RECORD_COLUMNS,
        )

    def test_clean_records_golden_totals(self) -> None:
        records = build_clean_records(self.factory, days=120, seed=42)
        self.assertEqual(len(records), 600)
        self.assertTrue(all(r.record_id is None for r in records))

        counts_by_machine = Counter(r.machine_id for r in records)
        self.assertEqual(
            dict(counts_by_machine),
            {"M1": 120, "M2": 240, "M3": 120, "M5": 120},
        )
        self.assertEqual(sum(r.planned_units for r in records), 322489)
        self.assertEqual(sum(r.actual_units for r in records), 298071)
        self.assertAlmostEqual(sum(r.downtime_hours for r in records), 238.0, delta=0.01)

    def test_inject_faults_golden_values_and_immutability(self) -> None:
        clean_snapshot = self.clean_raw_df.copy(deep=True)
        dirty_df, fault_log_df = inject_faults(self.clean_raw_df, seed=42)

        # Input clean_df must not be modified
        pd.testing.assert_frame_equal(self.clean_raw_df, clean_snapshot)

        # Row counts
        self.assertEqual(len(dirty_df), 610)
        self.assertEqual(len(fault_log_df), 76)
        self.assertEqual(list(fault_log_df.columns), ["record_id", "fault_type"])

        # Fault counts per type
        expected_counts = dict(FAULT_PLAN)
        expected_counts["duplicate_key"] = DUPLICATE_COUNT
        actual_counts = fault_log_df["fault_type"].value_counts().to_dict()
        self.assertEqual(actual_counts, expected_counts)

        # First 5 corrupted rows: indices [249, 575, 293, 39, 490] -> record_id [250, 576, 294, 40, 491]
        self.assertEqual(
            fault_log_df["record_id"].iloc[:5].tolist(),
            [250, 576, 294, 40, 491],
        )
        self.assertEqual(
            fault_log_df["fault_type"].iloc[:5].tolist(),
            ["missing_actual_units"] * 5,
        )

        # Duplicate rows have record_id 601..610 and first 5 come from record_id [55, 201, 261, 176, 327]
        dup_log = fault_log_df.iloc[66:]
        self.assertEqual(dup_log["record_id"].tolist(), list(range(601, 611)))
        self.assertTrue((dup_log["fault_type"] == "duplicate_key").all())

        key_cols = ["production_date", "shift", "machine_id", "product_code", "planned_units"]
        for copy_offset, expected_src_id in enumerate([55, 201, 261, 176, 327]):
            copy_row = dirty_df.iloc[600 + copy_offset]
            src_row = self.clean_raw_df.iloc[expected_src_id - 1]
            self.assertEqual(copy_row["record_id"], str(601 + copy_offset))
            for col in key_cols:
                self.assertEqual(copy_row[col], src_row[col])

        # Verify injected values for each fault category
        corrupted_log = fault_log_df.iloc[:66]
        for rid_val, ftype_val in zip(
            corrupted_log["record_id"].tolist(),
            corrupted_log["fault_type"].tolist(),
        ):
            rid = int(rid_val)
            ftype = str(ftype_val)
            row_idx = rid - 1
            dirty_row = dirty_df.iloc[row_idx]
            orig_row = self.clean_raw_df.iloc[row_idx]

            if ftype == "missing_actual_units":
                self.assertTrue(pd.isna(dirty_row["actual_units"]))
            elif ftype == "missing_downtime_hours":
                self.assertTrue(pd.isna(dirty_row["downtime_hours"]))
            elif ftype == "negative_actual_units":
                expected_neg = str(-(int(orig_row["actual_units"]) + 1))
                self.assertEqual(dirty_row["actual_units"], expected_neg)
            elif ftype == "non_numeric_actual_units":
                self.assertEqual(dirty_row["actual_units"], "abc")
            elif ftype == "downtime_too_high":
                self.assertEqual(dirty_row["downtime_hours"], "9.5")
            elif ftype == "invalid_shift":
                self.assertEqual(dirty_row["shift"], "evening")
            elif ftype == "unknown_machine_id":
                self.assertEqual(dirty_row["machine_id"], "M9")
            elif ftype == "invalid_date":
                self.assertEqual(dirty_row["production_date"], "2026-13-40")
            elif ftype == "zero_planned_units":
                self.assertEqual(dirty_row["planned_units"], "0")

    def test_reproducibility_with_same_seed(self) -> None:
        dirty1, log1 = inject_faults(self.clean_raw_df, seed=42)
        dirty2, log2 = inject_faults(self.clean_raw_df, seed=42)

        pd.testing.assert_frame_equal(dirty1, dirty2)
        pd.testing.assert_frame_equal(log1, log2)

    def test_write_raw_datasets_and_csv_json_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            info = write_raw_datasets(self.factory, tmp_dir, days=120, seed=42)

            self.assertEqual(
                info["row_counts"],
                {"clean": 600, "dirty": 610, "fault_log": 76},
            )

            # MP3 RecordStore readability on raw_records_clean.csv
            store = RecordStore(info["clean_path"])
            stored_records = store.get_all()
            self.assertEqual(len(stored_records), 600)
            self.assertEqual([r.record_id for r in stored_records], list(range(1, 601)))
            self.assertEqual(sum(r.planned_units for r in stored_records), 322489)
            self.assertEqual(sum(r.actual_units for r in stored_records), 298071)
            self.assertAlmostEqual(
                sum(r.downtime_hours for r in stored_records), 238.0, delta=0.01
            )

            # Dirty CSV and JSON loaded via load_records_dataframe must be identical
            dirty_csv_df = load_records_dataframe(info["dirty_csv_path"])
            dirty_json_df = load_records_dataframe(info["dirty_json_path"])

            pd.testing.assert_frame_equal(dirty_csv_df, dirty_json_df, check_dtype=False)
            self.assertEqual(len(dirty_csv_df), 610)
            self.assertEqual(int(dirty_csv_df["actual_units"].isna().sum()), 12)
            self.assertEqual(int(dirty_csv_df["downtime_hours"].isna().sum()), 12)
            for col in RECORD_COLUMNS:
                self.assertEqual(str(dirty_csv_df[col].dtype), "string")
                self.assertEqual(str(dirty_json_df[col].dtype), "string")

            # Check JSON file types directly: valid numbers are numbers, corrupt are str, missing are None
            with open(info["dirty_json_path"], encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["records"]), 610)
            # Record 250 (index 249) has missing_actual_units -> None in JSON, int planned_units
            rec_250 = payload["records"][249]
            self.assertIsNone(rec_250["actual_units"])
            self.assertIsInstance(rec_250["planned_units"], int)

    def test_invalid_inputs_raise_errors(self) -> None:
        with self.assertRaises(TypeError):
            inject_faults("not a df")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            inject_faults(self.clean_raw_df, seed="42")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            inject_faults(self.clean_raw_df, seed=-1)
        with self.assertRaises(ValueError):
            inject_faults(self.clean_raw_df.iloc[:20])

        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                save_dirty_records(
                    self.clean_raw_df,
                    str(Path(tmp_dir) / "wrong.txt"),
                    str(Path(tmp_dir) / "ok.json"),
                )


if __name__ == "__main__":
    unittest.main()
