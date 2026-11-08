"""
test_cleaning.py - Unit tests for cleaning.py (Kişi B).

Covers plan Section 3.3, Section 7.3 and the cleaning part of Section 7.7:
- Golden values of the 610-row dirty data set (610 -> 546 rows, 64 dropped,
  12 filled, 76 log rows, issue counts) and their invariants.
- The log matches the fault injection log of Kişi A row by row.
- Small hand-written frames for the boundary cases 1-10 of Section 7.3.
- Missing and invalid values are kept apart; several issues of one row give
  several log rows but a single drop.
- Inputs are not modified; no FutureWarning / SettingWithCopyWarning.
- Wrong inputs raise TypeError / ValueError with Turkish messages.

Author: Kişi B
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import re
import unittest
import warnings
from pathlib import Path

import pandas as pd

from factory_model.serialization import load_factory_json
from production_analysis.cleaning import clean_records, summarize_cleaning
from production_analysis.loading import (
    dataframe_to_records,
    load_records_dataframe,
    records_to_dataframe,
)
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.schema import CLEANING_LOG_COLUMNS, ISSUE_ACTIONS, RECORD_COLUMNS
from production_records.storage import load_records_csv

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
FACTORY_PATH = DATA_DIR / "sample_factory.json"
DIRTY_CSV_PATH = DATA_DIR / "raw_records_dirty.csv"
DIRTY_JSON_PATH = DATA_DIR / "raw_records_dirty.json"
CLEAN_RAW_PATH = DATA_DIR / "raw_records_clean.csv"
FAULT_LOG_PATH = DATA_DIR / "fault_injection_log.csv"

REAL_DATA_READY = all(
    path.is_file() for path in (DIRTY_CSV_PATH, DIRTY_JSON_PATH, CLEAN_RAW_PATH, FAULT_LOG_PATH)
)
REAL_DATA_REASON = "Kişi A'nın kirli veri dosyaları (data/raw_records_*.csv/json) bulunamadı."

#: Section 7.3 golden issue counts.
GOLDEN_ISSUE_COUNTS = {
    "missing_actual_units": 12,
    "invalid_actual_units": 12,
    "invalid_downtime_hours": 6,
    "invalid_shift": 6,
    "unknown_machine_id": 6,
    "invalid_date": 6,
    "invalid_planned_units": 6,
    "missing_downtime_hours": 12,
    "duplicate_key": 10,
}

#: Fault type of the injection log (Kişi A) -> issue code of the cleaning log.
FAULT_TO_ISSUE = {
    "missing_actual_units": "missing_actual_units",
    "missing_downtime_hours": "missing_downtime_hours",
    "negative_actual_units": "invalid_actual_units",
    "non_numeric_actual_units": "invalid_actual_units",
    "downtime_too_high": "invalid_downtime_hours",
    "invalid_shift": "invalid_shift",
    "unknown_machine_id": "unknown_machine_id",
    "invalid_date": "invalid_date",
    "zero_planned_units": "invalid_planned_units",
    "duplicate_key": "duplicate_key",
}

_BASE_ROW = {
    "record_id": "1",
    "production_date": "2026-10-01",
    "shift": "morning",
    "machine_id": "M1",
    "product_code": "P-A",
    "planned_units": "800",
    "actual_units": "780",
    "downtime_hours": "0.5",
}


def _strict_warnings(test: unittest.TestCase) -> None:
    """Turn pandas FutureWarning / SettingWithCopyWarning into errors for *test*."""
    manager = warnings.catch_warnings()
    manager.__enter__()
    test.addCleanup(manager.__exit__, None, None, None)
    warnings.simplefilter("error", FutureWarning)
    setting_with_copy = getattr(pd.errors, "SettingWithCopyWarning", None)
    if setting_with_copy is not None:
        warnings.simplefilter("error", setting_with_copy)


def _masters() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (machine_master, product_master) of the MP2 sample factory."""
    factory = load_factory_json(str(FACTORY_PATH))
    return build_machine_master(factory), build_product_master(factory)


def _raw(*rows: dict) -> pd.DataFrame:
    """Build a raw string frame; each row overrides fields of a valid base row.

    ``None`` stands for a missing value.  record_id defaults to 1, 2, 3 ...
    and the date to consecutive days so that the base rows never collide.
    """
    data = []
    for position, overrides in enumerate(rows):  # test data builder
        row = dict(_BASE_ROW)
        row["record_id"] = str(position + 1)
        row["production_date"] = (pd.Timestamp("2026-10-01") + pd.Timedelta(days=position)).strftime(
            "%Y-%m-%d"
        )
        row.update(overrides)
        data.append(row)
    return pd.DataFrame(data, columns=RECORD_COLUMNS, dtype=object).astype("string")


def _log_pairs(log: pd.DataFrame) -> set:
    """Return the cleaning log as a set of (record_id, issue)."""
    return set(zip(log["record_id"].astype(int).tolist(), log["issue"].astype(str).tolist()))


# ---------------------------------------------------------------------------
# Golden values (Section 7.3) on the real 610-row dirty data set
# ---------------------------------------------------------------------------

@unittest.skipUnless(REAL_DATA_READY, REAL_DATA_REASON)
class TestCleaningGoldenValues(unittest.TestCase):
    """Section 7.3 golden values and invariants on Kişi A's dirty data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()
        cls.raw_df = load_records_dataframe(str(DIRTY_CSV_PATH))
        cls.clean_df, cls.log_df = clean_records(cls.raw_df, cls.machine_master, cls.product_master)
        cls.summary = summarize_cleaning(cls.raw_df, cls.clean_df, cls.log_df)
        cls.fault_log = pd.read_csv(FAULT_LOG_PATH, dtype={"record_id": "int64", "fault_type": "string"})

    def setUp(self) -> None:
        _strict_warnings(self)

    def test_row_counts(self) -> None:
        self.assertEqual(self.summary["raw_row_count"], 610)
        self.assertEqual(self.summary["clean_row_count"], 546)
        self.assertEqual(len(self.clean_df), 546)

    def test_dropped_and_filled_counts(self) -> None:
        self.assertEqual(self.summary["dropped_row_count"], 64)
        self.assertEqual(self.summary["filled_row_count"], 12)
        self.assertEqual(
            self.summary["raw_row_count"] - self.summary["clean_row_count"],
            self.summary["dropped_row_count"],
        )

    def test_log_row_count_and_columns(self) -> None:
        self.assertEqual(len(self.log_df), 76)
        self.assertEqual(list(self.log_df.columns), CLEANING_LOG_COLUMNS)

    def test_issue_counts(self) -> None:
        self.assertEqual(self.summary["issue_counts"], GOLDEN_ISSUE_COUNTS)

    def test_log_actions_follow_issue_actions(self) -> None:
        expected = self.log_df["issue"].astype(str).map(ISSUE_ACTIONS)
        self.assertTrue((self.log_df["action"].astype(str) == expected).all())
        self.assertEqual(int((self.log_df["action"] == "dropped").sum()), 64)
        self.assertEqual(int((self.log_df["action"] == "filled").sum()), 12)

    def test_log_matches_fault_injection_log(self) -> None:
        expected = set(
            zip(
                self.fault_log["record_id"].tolist(),
                self.fault_log["fault_type"].astype(str).map(FAULT_TO_ISSUE).tolist(),
            )
        )
        self.assertEqual(_log_pairs(self.log_df), expected)

    def test_no_dropped_record_in_clean_data(self) -> None:
        dropped = self.log_df.loc[self.log_df["action"] == "dropped", "record_id"]
        self.assertFalse(self.clean_df["record_id"].isin(dropped).any())
        copies = set(range(601, 611))
        self.assertTrue(copies.isdisjoint(set(self.clean_df["record_id"].tolist())))
        duplicate_ids = set(
            self.log_df.loc[self.log_df["issue"] == "duplicate_key", "record_id"].tolist()
        )
        self.assertEqual(duplicate_ids, copies)

    def test_filled_rows_kept_with_zero_downtime(self) -> None:
        filled = self.log_df.loc[self.log_df["action"] == "filled", "record_id"]
        rows = self.clean_df[self.clean_df["record_id"].isin(filled)]
        self.assertEqual(len(rows), 12)
        self.assertTrue((rows["downtime_hours"] == 0.0).all())
        raw_missing = self.raw_df.loc[self.raw_df["downtime_hours"].isna(), "record_id"].astype(int)
        self.assertEqual(set(raw_missing.tolist()), set(filled.tolist()))

    def test_other_534_rows_equal_raw_clean_csv(self) -> None:
        reference = records_to_dataframe(load_records_csv(str(CLEAN_RAW_PATH)))
        filled = self.log_df.loc[self.log_df["action"] == "filled", "record_id"]
        untouched = self.clean_df[~self.clean_df["record_id"].isin(filled)].reset_index(drop=True)
        self.assertEqual(len(untouched), 534)
        expected = (
            reference[reference["record_id"].isin(untouched["record_id"])]
            .sort_values("record_id")
            .reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(untouched, expected, check_dtype=False)

    def test_sorted_by_record_id_without_duplicate_keys(self) -> None:
        self.assertTrue(self.clean_df["record_id"].is_monotonic_increasing)
        self.assertTrue(self.clean_df["record_id"].is_unique)
        self.assertEqual(list(self.clean_df.index), list(range(546)))
        key = ["production_date", "shift", "machine_id"]
        self.assertFalse(self.clean_df.duplicated(subset=key).any())

    def test_column_order_and_types(self) -> None:
        self.assertEqual(list(self.clean_df.columns), RECORD_COLUMNS)
        for column in ("record_id", "planned_units", "actual_units"):
            self.assertTrue(pd.api.types.is_integer_dtype(self.clean_df[column]), column)
        self.assertTrue(pd.api.types.is_float_dtype(self.clean_df["downtime_hours"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.clean_df["production_date"]))
        for column in ("shift", "machine_id", "product_code"):
            self.assertTrue(pd.api.types.is_string_dtype(self.clean_df[column]), column)

    def test_mp3_data_rules_hold(self) -> None:
        df = self.clean_df
        self.assertTrue((df["planned_units"] > 0).all())
        self.assertTrue((df["actual_units"] >= 0).all())
        self.assertTrue(df["downtime_hours"].between(0.0, 8.0).all())
        self.assertTrue(df["shift"].isin(["morning", "afternoon", "night"]).all())
        self.assertTrue(df["machine_id"].isin(self.machine_master["machine_id"]).all())
        self.assertTrue(df["product_code"].isin(self.product_master["product_code"]).all())
        self.assertFalse(df.isna().any().any())

    def test_all_rows_pass_mp3_validation(self) -> None:
        records = dataframe_to_records(self.clean_df)
        self.assertEqual(len(records), 546)

    def test_totals_match_section_7_5(self) -> None:
        self.assertEqual(int(self.clean_df["planned_units"].sum()), 293032)
        self.assertEqual(int(self.clean_df["actual_units"].sum()), 270519)
        self.assertAlmostEqual(float(self.clean_df["downtime_hours"].sum()), 223.375, delta=0.01)

    def test_csv_and_json_give_same_result(self) -> None:
        raw_json = load_records_dataframe(str(DIRTY_JSON_PATH))
        clean_json, log_json = clean_records(raw_json, self.machine_master, self.product_master)
        pd.testing.assert_frame_equal(clean_json, self.clean_df, check_dtype=False)
        pd.testing.assert_frame_equal(log_json, self.log_df, check_dtype=False)

    def test_raw_clean_file_has_no_issue(self) -> None:
        raw_clean = load_records_dataframe(str(CLEAN_RAW_PATH))
        clean_df, log_df = clean_records(raw_clean, self.machine_master, self.product_master)
        self.assertEqual(len(clean_df), 600)
        self.assertEqual(len(log_df), 0)

    def test_inputs_are_not_modified(self) -> None:
        raw_df = load_records_dataframe(str(DIRTY_CSV_PATH))
        machine_master, product_master = _masters()
        raw_copy, machine_copy, product_copy = raw_df.copy(), machine_master.copy(), product_master.copy()
        clean_records(raw_df, machine_master, product_master)
        pd.testing.assert_frame_equal(raw_df, raw_copy)
        pd.testing.assert_frame_equal(machine_master, machine_copy)
        pd.testing.assert_frame_equal(product_master, product_copy)


# ---------------------------------------------------------------------------
# Boundary cases (Section 7.3 table, cases 1-10) with small frames
# ---------------------------------------------------------------------------

class TestCleaningBoundaryCases(unittest.TestCase):
    """Hand-written frames for the Section 7.3 boundary cases."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()

    def setUp(self) -> None:
        _strict_warnings(self)

    def _clean(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        return clean_records(raw_df, self.machine_master, self.product_master)

    def test_case_1_planned_units_integer_valued(self) -> None:
        clean_df, log_df = self._clean(_raw({"planned_units": "800.0"}, {"planned_units": "800.5"}))
        self.assertEqual(clean_df["record_id"].tolist(), [1])
        self.assertEqual(int(clean_df.loc[0, "planned_units"]), 800)
        self.assertEqual(_log_pairs(log_df), {(2, "invalid_planned_units")})

    def test_case_2_downtime_bounds(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"downtime_hours": "8"},
                {"downtime_hours": "8.01"},
                {"downtime_hours": "-0.25"},
                {"downtime_hours": "0"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [1, 4])
        self.assertEqual(clean_df["downtime_hours"].tolist(), [8.0, 0.0])
        self.assertEqual(
            _log_pairs(log_df), {(2, "invalid_downtime_hours"), (3, "invalid_downtime_hours")}
        )

    def test_case_3_actual_units_zero_is_valid(self) -> None:
        clean_df, log_df = self._clean(_raw({"actual_units": "0"}))
        self.assertEqual(clean_df["actual_units"].tolist(), [0])
        self.assertEqual(len(log_df), 0)

    def test_case_4_whitespace_shift_is_missing_key_field(self) -> None:
        clean_df, log_df = self._clean(_raw({"shift": " "}))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "missing_key_field")})

    def test_case_5_invalid_dates(self) -> None:
        clean_df, log_df = self._clean(
            _raw({"production_date": "2026-02-30"}, {"production_date": "01.10.2026"})
        )
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "invalid_date"), (2, "invalid_date")})

    def test_case_5b_non_padded_iso_date_is_invalid(self) -> None:
        # MP3 requires YYYY-MM-DD with two-digit month and day.
        clean_df, log_df = self._clean(_raw({"production_date": "2026-1-05"}))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "invalid_date")})

    def test_case_6_unknown_product_code(self) -> None:
        clean_df, log_df = self._clean(_raw({"product_code": "P-Z"}))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "unknown_product_code")})

    def test_case_7_unavailable_machine_is_valid(self) -> None:
        clean_df, log_df = self._clean(_raw({"machine_id": "M4"}))
        self.assertEqual(clean_df["machine_id"].tolist(), ["M4"])
        self.assertEqual(len(log_df), 0)

    def test_case_8_duplicate_keeps_smallest_record_id(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"record_id": "5", "production_date": "2026-10-01"},
                {"record_id": "3", "production_date": "2026-10-01"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [3])
        self.assertEqual(_log_pairs(log_df), {(5, "duplicate_key")})
        self.assertEqual(log_df["action"].tolist(), ["dropped"])

    def test_case_9_two_issues_one_drop(self) -> None:
        raw_df = _raw({}, {"shift": "evening", "actual_units": "abc"})
        clean_df, log_df = self._clean(raw_df)
        self.assertEqual(clean_df["record_id"].tolist(), [1])
        self.assertEqual(log_df["record_id"].tolist(), [2, 2])
        self.assertEqual(log_df["issue"].tolist(), ["invalid_shift", "invalid_actual_units"])
        summary = summarize_cleaning(raw_df, clean_df, log_df)
        self.assertEqual(summary["dropped_row_count"], 1)
        self.assertEqual(summary["issue_counts"], {"invalid_shift": 1, "invalid_actual_units": 1})

    def test_case_10_empty_raw_frame(self) -> None:
        empty = pd.DataFrame({column: pd.array([], dtype="string") for column in RECORD_COLUMNS})
        clean_df, log_df = self._clean(empty)
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(len(log_df), 0)
        self.assertEqual(list(clean_df.columns), RECORD_COLUMNS)
        self.assertEqual(list(log_df.columns), CLEANING_LOG_COLUMNS)
        summary = summarize_cleaning(empty, clean_df, log_df)
        self.assertEqual(
            summary,
            {
                "raw_row_count": 0,
                "clean_row_count": 0,
                "dropped_row_count": 0,
                "filled_row_count": 0,
                "issue_counts": {},
            },
        )


# ---------------------------------------------------------------------------
# Further rules of Section 3.3
# ---------------------------------------------------------------------------

class TestCleaningRules(unittest.TestCase):
    """Missing vs invalid, fill rule, duplicate order and error handling."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()

    def setUp(self) -> None:
        _strict_warnings(self)

    def _clean(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        return clean_records(raw_df, self.machine_master, self.product_master)

    def test_missing_and_invalid_are_separate(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"actual_units": None},
                {"actual_units": "abc"},
                {"actual_units": "-3"},
                {"actual_units": "10.5"},
                {"planned_units": None},
                {"planned_units": "0"},
                {"production_date": None},
                {"production_date": "2026-13-40"},
            )
        )
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(
            _log_pairs(log_df),
            {
                (1, "missing_actual_units"),
                (2, "invalid_actual_units"),
                (3, "invalid_actual_units"),
                (4, "invalid_actual_units"),
                (5, "missing_key_field"),
                (6, "invalid_planned_units"),
                (7, "missing_key_field"),
                (8, "invalid_date"),
            },
        )

    def test_each_missing_key_field_is_reported(self) -> None:
        rows = [{field: None} for field in ("production_date", "shift", "machine_id", "product_code")]
        clean_df, log_df = self._clean(_raw(*rows))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(log_df["issue"].tolist(), ["missing_key_field"] * 4)

    def test_several_missing_key_fields_give_one_issue_row(self) -> None:
        clean_df, log_df = self._clean(_raw({"shift": None, "machine_id": "", "product_code": None}))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "missing_key_field")})

    def test_only_downtime_is_filled(self) -> None:
        clean_df, log_df = self._clean(_raw({"downtime_hours": None}, {"downtime_hours": "  "}))
        self.assertEqual(clean_df["record_id"].tolist(), [1, 2])
        self.assertEqual(clean_df["downtime_hours"].tolist(), [0.0, 0.0])
        self.assertEqual(log_df["action"].tolist(), ["filled", "filled"])
        self.assertEqual(log_df["issue"].tolist(), ["missing_downtime_hours"] * 2)

    def test_dropped_row_with_missing_downtime_is_not_counted_as_filled(self) -> None:
        raw_df = _raw({"downtime_hours": None, "shift": "evening"})
        clean_df, log_df = self._clean(raw_df)
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(
            _log_pairs(log_df), {(1, "missing_downtime_hours"), (1, "invalid_shift")}
        )
        summary = summarize_cleaning(raw_df, clean_df, log_df)
        self.assertEqual(summary["dropped_row_count"], 1)
        self.assertEqual(summary["filled_row_count"], 0)

    def test_duplicate_check_runs_after_drop(self) -> None:
        # record 1 is invalid and dropped first, so record 2 is not a duplicate.
        clean_df, log_df = self._clean(
            _raw(
                {"production_date": "2026-10-01", "actual_units": "abc"},
                {"production_date": "2026-10-01"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [2])
        self.assertEqual(_log_pairs(log_df), {(1, "invalid_actual_units")})

    def test_duplicate_key_uses_date_shift_machine_only(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"production_date": "2026-10-01"},
                {"production_date": "2026-10-01", "shift": "afternoon"},
                {"production_date": "2026-10-01", "machine_id": "M2"},
                {"production_date": "2026-10-01", "product_code": "P-B", "actual_units": "1"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [1, 2, 3])
        self.assertEqual(_log_pairs(log_df), {(4, "duplicate_key")})

    def test_three_copies_keep_smallest(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"record_id": "9", "production_date": "2026-10-05"},
                {"record_id": "2", "production_date": "2026-10-05"},
                {"record_id": "7", "production_date": "2026-10-05"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [2])
        self.assertEqual(log_df["record_id"].tolist(), [7, 9])

    def test_result_sorted_by_record_id_and_log_sorted(self) -> None:
        clean_df, log_df = self._clean(
            _raw(
                {"record_id": "30", "actual_units": "abc", "shift": "x"},
                {"record_id": "10"},
                {"record_id": "20", "downtime_hours": "9.5"},
            )
        )
        self.assertEqual(clean_df["record_id"].tolist(), [10])
        self.assertEqual(log_df["record_id"].tolist(), [20, 30, 30])
        self.assertEqual(
            log_df["issue"].tolist(),
            ["invalid_downtime_hours", "invalid_shift", "invalid_actual_units"],
        )

    def test_values_are_not_corrected(self) -> None:
        clean_df, log_df = self._clean(_raw({"shift": "Morning"}, {"machine_id": " M1"}))
        self.assertEqual(len(clean_df), 0)
        self.assertEqual(_log_pairs(log_df), {(1, "invalid_shift"), (2, "unknown_machine_id")})

    def test_typed_input_frame_is_accepted(self) -> None:
        typed = _raw({}).astype({"record_id": "int64", "planned_units": "int64"})
        clean_df, log_df = self._clean(typed)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(len(log_df), 0)

    def test_extra_columns_are_ignored(self) -> None:
        raw_df = _raw({}).assign(note="x")
        clean_df, _ = self._clean(raw_df)
        self.assertEqual(list(clean_df.columns), RECORD_COLUMNS)

    def test_index_of_input_does_not_matter(self) -> None:
        raw_df = _raw({}, {"actual_units": "abc"})
        raw_df.index = [10, 5]
        clean_df, log_df = self._clean(raw_df)
        self.assertEqual(clean_df["record_id"].tolist(), [1])
        self.assertEqual(list(clean_df.index), [0])
        self.assertEqual(_log_pairs(log_df), {(2, "invalid_actual_units")})

    def test_inputs_not_modified_small(self) -> None:
        raw_df = _raw({"downtime_hours": None}, {"shift": " "})
        raw_copy = raw_df.copy()
        self._clean(raw_df)
        pd.testing.assert_frame_equal(raw_df, raw_copy)


class TestCleaningErrors(unittest.TestCase):
    """Section 7.7 cleaning errors (Turkish messages)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()

    def setUp(self) -> None:
        _strict_warnings(self)

    def test_list_instead_of_frame_raises_type_error(self) -> None:
        with self.assertRaisesRegex(TypeError, "DataFrame olmalıdır"):
            clean_records([_BASE_ROW], self.machine_master, self.product_master)
        with self.assertRaises(TypeError):
            clean_records(_raw({}), [], self.product_master)
        with self.assertRaises(TypeError):
            summarize_cleaning(_raw({}), [], pd.DataFrame(columns=CLEANING_LOG_COLUMNS))

    def test_missing_raw_column_raises_value_error(self) -> None:
        raw_df = _raw({}).drop(columns="actual_units")
        with self.assertRaisesRegex(ValueError, "gerekli sütun.*actual_units"):
            clean_records(raw_df, self.machine_master, self.product_master)

    def test_missing_master_column_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "machine_master.*machine_id"):
            clean_records(_raw({}), self.machine_master.drop(columns="machine_id"), self.product_master)
        with self.assertRaisesRegex(ValueError, "product_master.*product_code"):
            clean_records(_raw({}), self.machine_master, self.product_master.drop(columns="product_code"))

    def test_invalid_record_id_raises_value_error(self) -> None:
        for bad in (None, "abc", "0", "1.5"):
            with self.subTest(record_id=bad):
                with self.assertRaisesRegex(ValueError, "record_id"):
                    clean_records(_raw({"record_id": bad}), self.machine_master, self.product_master)

    def test_repeated_record_id_raises_value_error(self) -> None:
        raw_df = _raw({"record_id": "4"}, {"record_id": "4"})
        with self.assertRaisesRegex(ValueError, "benzersiz"):
            clean_records(raw_df, self.machine_master, self.product_master)


class TestCleaningSourceRules(unittest.TestCase):
    """Section 7.6 #7: no row iteration in cleaning.py."""

    def test_no_row_iteration(self) -> None:
        source = (PROJECT_DIR / "production_analysis" / "cleaning.py").read_text(encoding="utf-8")
        for pattern in (r"\.iterrows\(", r"\.itertuples\(", r"\.apply\(", r"iterrows", r"itertuples"):
            self.assertIsNone(re.search(pattern, source), pattern)

    def test_no_print_or_input(self) -> None:
        source = (PROJECT_DIR / "production_analysis" / "cleaning.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\bprint\(|\binput\(", source))


if __name__ == "__main__":
    unittest.main()
