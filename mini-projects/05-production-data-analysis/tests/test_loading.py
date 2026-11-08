"""
test_loading.py - Unit tests for loading.py (Kişi A).

Covers Section 3.2, Section 5 (Stage 3), Section 7.6 (#6) and Section 7.7:
- load_records_dataframe loads CSV and JSON into identical raw string
  DataFrames (pandas string dtype, <NA> for missing/blank).
- Empty (0-byte) files return an empty raw frame with RECORD_COLUMNS.
- Unsupported extensions, missing files, wrong CSV headers, missing 'records'
  key or corrupt JSON raise ValueError with Turkish messages.
- records_to_dataframe and dataframe_to_records perform lossless round-trip
  conversions and enforce MP3 ProductionRecord validation.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from production_analysis.loading import (
    dataframe_to_records,
    load_records_dataframe,
    records_to_dataframe,
)
from production_analysis.schema import RECORD_COLUMNS
from production_records.storage import load_records_csv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TEST_CSV_PATH = DATA_DIR / "test_records.csv"
TEST_JSON_PATH = DATA_DIR / "test_records.json"


class TestLoadRecordsDataFrame(unittest.TestCase):
    """Test raw CSV and JSON loading into string DataFrames."""

    def test_load_csv_and_json_produce_identical_frame(self) -> None:
        df_csv = load_records_dataframe(str(TEST_CSV_PATH))
        df_json = load_records_dataframe(str(TEST_JSON_PATH))

        self.assertEqual(list(df_csv.columns), RECORD_COLUMNS)
        self.assertEqual(len(df_csv), 8)
        for col in RECORD_COLUMNS:
            self.assertEqual(str(df_csv[col].dtype), "string")
            self.assertEqual(str(df_json[col].dtype), "string")

        pd.testing.assert_frame_equal(df_csv, df_json, check_dtype=False)

    def test_blank_and_whitespace_values_become_na_while_corrupt_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "dirty.csv")
            json_path = os.path.join(tmp_dir, "dirty.json")

            csv_content = (
                ",".join(RECORD_COLUMNS) + "\r\n"
                "1,2026-10-01,morning,M1,P-A,800,,0.5\r\n"
                "2,2026-13-40,   ,M9,P-B,0,abc,9.5\r\n"
            )
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                fh.write(csv_content)

            json_payload = {
                "schema_version": 1,
                "records": [
                    {
                        "record_id": 1,
                        "production_date": "2026-10-01",
                        "shift": "morning",
                        "machine_id": "M1",
                        "product_code": "P-A",
                        "planned_units": 800,
                        "actual_units": None,
                        "downtime_hours": 0.5,
                    },
                    {
                        "record_id": 2,
                        "production_date": "2026-13-40",
                        "shift": "   ",
                        "machine_id": "M9",
                        "product_code": "P-B",
                        "planned_units": 0,
                        "actual_units": "abc",
                        "downtime_hours": 9.5,
                    },
                ],
            }
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(json_payload, fh)

            df_csv = load_records_dataframe(csv_path)
            df_json = load_records_dataframe(json_path)

            pd.testing.assert_frame_equal(df_csv, df_json, check_dtype=False)
            self.assertTrue(pd.isna(df_csv.loc[0, "actual_units"]))
            self.assertTrue(pd.isna(df_csv.loc[1, "shift"]))
            self.assertEqual(df_csv.loc[1, "actual_units"], "abc")
            self.assertEqual(df_csv.loc[1, "production_date"], "2026-13-40")

    def test_zero_byte_files_return_empty_raw_dataframe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for ext in (".csv", ".json"):
                empty_path = os.path.join(tmp_dir, f"empty{ext}")
                with open(empty_path, "w", encoding="utf-8"):
                    pass
                df = load_records_dataframe(empty_path)
                self.assertEqual(len(df), 0)
                self.assertEqual(list(df.columns), RECORD_COLUMNS)
                for col in RECORD_COLUMNS:
                    self.assertEqual(str(df[col].dtype), "string")

    def test_invalid_paths_and_corrupt_files_raise_errors(self) -> None:
        with self.assertRaises(TypeError):
            load_records_dataframe(123)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            load_records_dataframe("   ")

        with tempfile.TemporaryDirectory() as tmp_dir:
            txt_path = os.path.join(tmp_dir, "records.txt")
            with open(txt_path, "w", encoding="utf-8") as fh:
                fh.write("hello")
            with self.assertRaises(ValueError):
                load_records_dataframe(txt_path)

            missing_path = os.path.join(tmp_dir, "does_not_exist.csv")
            with self.assertRaises(ValueError):
                load_records_dataframe(missing_path)

            bad_header_csv = os.path.join(tmp_dir, "bad_header.csv")
            with open(bad_header_csv, "w", encoding="utf-8") as fh:
                fh.write("id,date,shift\n1,2026-10-01,morning\n")
            with self.assertRaises(ValueError):
                load_records_dataframe(bad_header_csv)

            no_records_json = os.path.join(tmp_dir, "no_records.json")
            with open(no_records_json, "w", encoding="utf-8") as fh:
                json.dump({"schema_version": 1}, fh)
            with self.assertRaises(ValueError):
                load_records_dataframe(no_records_json)

            corrupt_json = os.path.join(tmp_dir, "corrupt.json")
            with open(corrupt_json, "w", encoding="utf-8") as fh:
                fh.write("{invalid json")
            with self.assertRaises(ValueError):
                load_records_dataframe(corrupt_json)


class TestBoundaryRecordConversions(unittest.TestCase):
    """Test records_to_dataframe and dataframe_to_records round-trip & validation."""

    def test_round_trip_records_and_dataframe(self) -> None:
        records = load_records_csv(str(TEST_CSV_PATH))
        df = records_to_dataframe(records)

        self.assertEqual(list(df.columns), RECORD_COLUMNS)
        self.assertEqual(len(df), 8)
        self.assertTrue(pd.api.types.is_integer_dtype(df["record_id"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["production_date"]))
        self.assertTrue(pd.api.types.is_integer_dtype(df["planned_units"]))
        self.assertTrue(pd.api.types.is_integer_dtype(df["actual_units"]))
        self.assertTrue(pd.api.types.is_float_dtype(df["downtime_hours"]))

        reconstructed = dataframe_to_records(df)
        self.assertEqual(reconstructed, records)

        df_again = records_to_dataframe(reconstructed)
        pd.testing.assert_frame_equal(df, df_again, check_dtype=False)

    def test_empty_records_round_trip(self) -> None:
        empty_df = records_to_dataframe([])
        self.assertEqual(len(empty_df), 0)
        self.assertEqual(list(empty_df.columns), RECORD_COLUMNS)
        self.assertEqual(dataframe_to_records(empty_df), [])

    def test_invalid_inputs_in_conversions_raise_errors(self) -> None:
        with self.assertRaises(TypeError):
            records_to_dataframe("not a list")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            records_to_dataframe([{"record_id": 1}])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            dataframe_to_records([1, 2, 3])  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            dataframe_to_records(pd.DataFrame({"record_id": [1]}))

        records = load_records_csv(str(TEST_CSV_PATH))
        df = records_to_dataframe(records)
        bad_df = df.copy()
        bad_df.loc[0, "planned_units"] = 0
        with self.assertRaises(ValueError):
            dataframe_to_records(bad_df)


if __name__ == "__main__":
    unittest.main()
