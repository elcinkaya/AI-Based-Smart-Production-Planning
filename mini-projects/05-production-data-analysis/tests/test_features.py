"""
test_features.py - Unit tests for features.py (Kişi B).

Covers plan Sections 3.2, 3.5, 7.4, the derived-column part of 7.5 and the
feature part of 7.7:
- Derived columns of the 8 fixed MP3 records (data/test_records.csv),
  verified by hand from the record values.
- Daily series (complete date range, missing days, 7-day moving average)
  and weekly summary (Monday week start, partial weeks).
- Full pipeline on Kişi A's dirty data: Section 7.5 values that depend only
  on the derived columns and the series.
- Section 7.4 per-record golden values of the plan that do NOT match the
  records in data/test_records.csv are kept unchanged in a skipped class
  (see its reason) and reproduced with the record values they imply.
- Inputs are not modified; wrong inputs raise TypeError / ValueError.

Author: Kişi B
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import re
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from factory_model.serialization import load_factory_json
from production_analysis.cleaning import clean_records
from production_analysis.features import (
    DAILY_SERIES_COLUMNS,
    WEEKLY_SUMMARY_COLUMNS,
    add_derived_columns,
    build_daily_series,
    build_weekly_summary,
)
from production_analysis.loading import load_records_dataframe, records_to_dataframe
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.schema import DERIVED_COLUMNS, RECORD_COLUMNS
from production_records.storage import load_records_csv

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
FACTORY_PATH = DATA_DIR / "sample_factory.json"
TEST_RECORDS_PATH = DATA_DIR / "test_records.csv"
DIRTY_CSV_PATH = DATA_DIR / "raw_records_dirty.csv"

REAL_DATA_READY = DIRTY_CSV_PATH.is_file()
REAL_DATA_REASON = "Kişi A'nın kirli veri dosyası (data/raw_records_dirty.csv) bulunamadı."

WORD_GOLDEN_MISMATCH_REASON = (
    "Plan 7.4 'Kayıt 1, 2, 4, 7' ve attainment_pct_std altın değerleri data/test_records.csv "
    "içindeki MP3 kayıtlarıyla üretilemiyor (ör. kayıt 2: 760/800 = %95,00, plan %105,26). "
    "Toplamlar (4510, 4366, 94,75 ...) tutuyor; değerler değiştirilmedi, ekip kararı bekleniyor."
)

DELTA = 0.01


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


def _typed(rows: list) -> pd.DataFrame:
    """Build a small clean_df from (id, date, shift, machine, product, plan, actual, downtime)."""
    frame = pd.DataFrame(rows, columns=RECORD_COLUMNS)
    return frame.astype(
        {
            "record_id": "int64",
            "shift": "string",
            "machine_id": "string",
            "product_code": "string",
            "planned_units": "int64",
            "actual_units": "int64",
            "downtime_hours": "float64",
        }
    ).assign(production_date=pd.to_datetime(frame["production_date"], format="%Y-%m-%d"))


# ---------------------------------------------------------------------------
# Section 7.4 - the 8 fixed MP3 records
# ---------------------------------------------------------------------------

class TestDerivedColumnsMp3Records(unittest.TestCase):
    """Derived columns of data/test_records.csv, verified by hand."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()
        raw_df = load_records_dataframe(str(TEST_RECORDS_PATH))
        cls.clean_df, cls.log_df = clean_records(raw_df, cls.machine_master, cls.product_master)
        cls.analysis_df = add_derived_columns(cls.clean_df, cls.machine_master, cls.product_master)

    def setUp(self) -> None:
        _strict_warnings(self)

    def _column(self, name: str) -> list:
        return self.analysis_df[name].tolist()

    def test_clean_input(self) -> None:
        self.assertEqual(len(self.clean_df), 8)
        self.assertEqual(len(self.log_df), 0)
        mp3_frame = records_to_dataframe(load_records_csv(str(TEST_RECORDS_PATH)))
        pd.testing.assert_frame_equal(self.clean_df, mp3_frame, check_dtype=False)

    def test_columns_and_row_order(self) -> None:
        self.assertEqual(list(self.analysis_df.columns), RECORD_COLUMNS + DERIVED_COLUMNS)
        self.assertEqual(self._column("record_id"), list(range(1, 9)))
        self.assertEqual(list(self.analysis_df.index), list(range(8)))
        pd.testing.assert_frame_equal(self.analysis_df[RECORD_COLUMNS], self.clean_df)

    def test_column_types(self) -> None:
        df = self.analysis_df
        for column in ("priority", "production_gap", "weekday"):
            self.assertTrue(pd.api.types.is_integer_dtype(df[column]), column)
        for column in (
            "shift_effective_capacity",
            "attainment_pct",
            "availability_pct",
            "capacity_utilization_pct",
        ):
            self.assertTrue(pd.api.types.is_float_dtype(df[column]), column)
        for column in ("plan_met", "has_downtime"):
            self.assertTrue(pd.api.types.is_bool_dtype(df[column]), column)
        self.assertTrue(pd.api.types.is_string_dtype(df["line_id"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["week_start"]))

    def test_master_columns(self) -> None:
        self.assertEqual(self._column("line_id"), ["L1", "L1", "L1", "L1", "L1", "L2", "L2", "L2"])
        self.assertEqual(self._column("priority"), [1, 2, 1, 1, 2, 2, 3, 2])
        self.assertTrue(
            np.allclose(
                self._column("shift_effective_capacity"), [816, 816, 816, 576, 576, 336, 336, 336]
            )
        )

    def test_production_gap(self) -> None:
        self.assertEqual(self._column("production_gap"), [-20, -40, -44, -5, -5, -10, -10, -10])
        self.assertEqual(int(self.analysis_df["production_gap"].sum()), -144)

    def test_attainment_pct(self) -> None:
        expected = [97.50, 95.00, 94.50, 99.115, 99.115, 96.970, 96.970, 96.875]
        self.assertTrue(np.allclose(self._column("attainment_pct"), expected, atol=DELTA))

    def test_record_1_matches_plan_golden(self) -> None:
        row = self.analysis_df.iloc[0]
        self.assertAlmostEqual(row["attainment_pct"], 97.50, delta=DELTA)
        self.assertAlmostEqual(row["capacity_utilization_pct"], 95.59, delta=DELTA)

    def test_availability_pct(self) -> None:
        expected = [93.75, 87.5, 87.5, 93.75, 93.75, 93.75, 93.75, 93.75]
        self.assertTrue(np.allclose(self._column("availability_pct"), expected))

    def test_capacity_utilization_pct(self) -> None:
        expected = [95.588, 93.137, 92.647, 97.222, 97.222, 95.238, 95.238, 92.262]
        self.assertTrue(np.allclose(self._column("capacity_utilization_pct"), expected, atol=DELTA))

    def test_capacity_utilization_totals_match_plan(self) -> None:
        df = self.analysis_df
        overall = df["actual_units"].sum() / df["shift_effective_capacity"].sum() * 100
        self.assertAlmostEqual(df["shift_effective_capacity"].sum(), 4608.0, delta=DELTA)
        self.assertAlmostEqual(overall, 94.75, delta=DELTA)
        grouped = df.groupby("machine_id").agg(
            actual=("actual_units", "sum"), capacity=("shift_effective_capacity", "sum")
        )
        by_machine = (grouped["actual"] / grouped["capacity"] * 100).to_dict()
        self.assertAlmostEqual(by_machine["M1"], 93.79, delta=DELTA)
        self.assertAlmostEqual(by_machine["M2"], 97.22, delta=DELTA)
        self.assertAlmostEqual(by_machine["M3"], 94.25, delta=DELTA)

    def test_mp3_totals(self) -> None:
        df = self.analysis_df
        planned, actual = int(df["planned_units"].sum()), int(df["actual_units"].sum())
        self.assertEqual((planned, actual, actual - planned), (4510, 4366, -144))
        self.assertAlmostEqual(actual / planned * 100, 96.81, delta=DELTA)
        self.assertAlmostEqual(df["downtime_hours"].sum(), 5.0, delta=DELTA)
        availability = (len(df) * 8 - df["downtime_hours"].sum()) / (len(df) * 8) * 100
        self.assertAlmostEqual(availability, 92.19, delta=DELTA)

    def test_flags(self) -> None:
        self.assertEqual(self._column("plan_met"), [False] * 8)
        self.assertEqual(self._column("has_downtime"), [True] * 8)

    def test_weekday_and_week_start(self) -> None:
        self.assertEqual(self._column("weekday"), [3, 4, 5, 3, 3, 3, 4, 5])
        self.assertTrue((self.analysis_df["week_start"] == pd.Timestamp("2026-09-28")).all())

    def test_weekly_summary(self) -> None:
        weekly = build_weekly_summary(self.analysis_df)
        self.assertEqual(list(weekly.columns), WEEKLY_SUMMARY_COLUMNS)
        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly.index[0], pd.Timestamp("2026-09-28"))
        row = weekly.iloc[0]
        self.assertEqual(int(row["day_count"]), 3)
        self.assertEqual(int(row["record_count"]), 8)
        self.assertFalse(bool(row["is_complete_week"]))
        self.assertEqual(int(row["total_planned_units"]), 4510)
        self.assertEqual(int(row["total_actual_units"]), 4366)
        self.assertEqual(int(row["production_gap"]), -144)
        self.assertAlmostEqual(row["total_downtime_hours"], 5.0, delta=DELTA)
        self.assertAlmostEqual(row["attainment_pct"], 96.81, delta=DELTA)

    def test_daily_series(self) -> None:
        daily = build_daily_series(self.analysis_df)
        self.assertEqual(list(daily.columns), DAILY_SERIES_COLUMNS)
        self.assertEqual(
            list(daily.index), list(pd.date_range("2026-10-01", "2026-10-03", freq="D"))
        )
        self.assertEqual(daily.index.name, "production_date")
        self.assertEqual(daily["record_count"].tolist(), [4, 2, 2])
        self.assertEqual(daily["total_planned_units"].tolist(), [2260, 1130, 1120])
        self.assertEqual(daily["total_actual_units"].tolist(), [2220, 1080, 1066])
        self.assertTrue(np.allclose(daily["total_downtime_hours"], [2.0, 1.5, 1.5]))
        self.assertEqual(daily["production_gap"].tolist(), [-40, -50, -54])
        self.assertTrue(np.allclose(daily["attainment_pct"], [98.230, 95.575, 95.179], atol=DELTA))
        self.assertTrue(daily["actual_units_ma7"].isna().all())
        self.assertFalse(daily["is_missing_day"].any())

    def test_daily_series_without_october_2(self) -> None:
        subset = self.analysis_df[self.analysis_df["production_date"] != pd.Timestamp("2026-10-02")]
        daily = build_daily_series(subset)
        self.assertEqual(len(daily), 3)
        day = daily.loc[pd.Timestamp("2026-10-02")]
        self.assertEqual(int(day["record_count"]), 0)
        self.assertEqual(int(day["total_planned_units"]), 0)
        self.assertEqual(int(day["total_actual_units"]), 0)
        self.assertEqual(float(day["total_downtime_hours"]), 0.0)
        self.assertEqual(int(day["production_gap"]), 0)
        self.assertTrue(np.isnan(day["attainment_pct"]))
        self.assertTrue(bool(day["is_missing_day"]))
        self.assertEqual(daily["is_missing_day"].tolist(), [False, True, False])


@unittest.skip(WORD_GOLDEN_MISMATCH_REASON)
class TestPlanGoldenRecordValuesUnchanged(unittest.TestCase):
    """Plan 7.4 values copied unchanged; skipped until the team resolves the data mismatch."""

    def test_records_1_2_4_7(self) -> None:
        machine_master, product_master = _masters()
        clean_df, _ = clean_records(
            load_records_dataframe(str(TEST_RECORDS_PATH)), machine_master, product_master
        )
        df = add_derived_columns(clean_df, machine_master, product_master).set_index("record_id")
        for record_id, attainment, utilization in (
            (1, 97.50, 95.59),
            (2, 105.26, 104.17),
            (4, 102.00, 100.00),
            (7, 87.50, 85.78),
        ):
            self.assertAlmostEqual(df.loc[record_id, "attainment_pct"], attainment, delta=DELTA)
            self.assertAlmostEqual(df.loc[record_id, "capacity_utilization_pct"], utilization, delta=DELTA)
        std = df.groupby("machine_id")["attainment_pct"].std(ddof=0)
        self.assertAlmostEqual(std["M1"], 6.06, delta=DELTA)
        self.assertAlmostEqual(std["M2"], 6.20, delta=DELTA)
        self.assertAlmostEqual(std["M3"], 4.29, delta=DELTA)


class TestPlanGoldenFormulaReproduction(unittest.TestCase):
    """Diagnostic: the plan 7.4 per-record values follow from the same formulas.

    The record values below are the ones implied by the plan numbers
    (e.g. 105.26 % and 104.17 % -> M2, 600 of 570 planned); they are not in
    data/test_records.csv.  Passing shows the mismatch is in the input data,
    not in add_derived_columns.
    """

    def setUp(self) -> None:
        _strict_warnings(self)

    def test_formulas_give_plan_values(self) -> None:
        machine_master, product_master = _masters()
        clean_df = _typed(
            [
                (1, "2026-10-01", "morning", "M1", "P-A", 800, 780, 0.5),
                (2, "2026-10-01", "morning", "M2", "P-B", 570, 600, 0.5),
                (4, "2026-10-02", "morning", "M1", "P-A", 800, 816, 0.0),
                (7, "2026-10-03", "morning", "M1", "P-B", 800, 700, 1.0),
            ]
        )
        df = add_derived_columns(clean_df, machine_master, product_master)
        self.assertTrue(np.allclose(df["attainment_pct"], [97.50, 105.26, 102.00, 87.50], atol=DELTA))
        self.assertTrue(
            np.allclose(df["capacity_utilization_pct"], [95.59, 104.17, 100.00, 85.78], atol=DELTA)
        )
        m1 = df.loc[df["machine_id"] == "M1", "attainment_pct"]
        self.assertAlmostEqual(m1.std(ddof=0), 6.06, delta=DELTA)
        self.assertAlmostEqual(m1.std(ddof=1), 7.42, delta=DELTA)


# ---------------------------------------------------------------------------
# Series rules (Section 3.5) with small frames
# ---------------------------------------------------------------------------

class TestSeriesRules(unittest.TestCase):
    """Moving average, missing days and Monday week start."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()

    def setUp(self) -> None:
        _strict_warnings(self)

    def _analysis(self, dates: list, actual: list) -> pd.DataFrame:
        rows = [
            (i + 1, date, "morning", "M1", "P-A", 100, value, 0.0)
            for i, (date, value) in enumerate(zip(dates, actual))  # test data builder
        ]
        return add_derived_columns(_typed(rows), self.machine_master, self.product_master)

    def test_moving_average_needs_seven_days(self) -> None:
        dates = [f"2026-10-{day:02d}" for day in range(1, 9)]
        daily = build_daily_series(self._analysis(dates, [10, 20, 30, 40, 50, 60, 70, 80]))
        ma7 = daily["actual_units_ma7"].tolist()
        self.assertTrue(all(np.isnan(value) for value in ma7[:6]))
        self.assertAlmostEqual(ma7[6], 40.0)
        self.assertAlmostEqual(ma7[7], 50.0)

    def test_missing_days_count_as_zero_in_moving_average(self) -> None:
        dates = ["2026-10-01", "2026-10-02", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07"]
        daily = build_daily_series(self._analysis(dates, [70, 70, 70, 70, 70, 70]))
        self.assertEqual(len(daily), 7)
        self.assertEqual(daily["is_missing_day"].tolist(), [False, False, True, False, False, False, False])
        self.assertAlmostEqual(daily["actual_units_ma7"].iloc[-1], 60.0)

    def test_dates_are_sorted_in_series(self) -> None:
        daily = build_daily_series(self._analysis(["2026-10-03", "2026-10-01"], [5, 7]))
        self.assertEqual(list(daily.index), list(pd.date_range("2026-10-01", "2026-10-03")))
        self.assertEqual(daily["total_actual_units"].tolist(), [7, 0, 5])

    def test_week_starts_on_monday(self) -> None:
        dates = ["2026-10-04", "2026-10-05", "2026-10-11", "2026-10-12"]  # Sun, Mon, Sun, Mon
        df = self._analysis(dates, [1, 1, 1, 1])
        self.assertEqual(df["weekday"].tolist(), [6, 0, 6, 0])
        self.assertEqual(
            df["week_start"].tolist(),
            [pd.Timestamp(d) for d in ("2026-09-28", "2026-10-05", "2026-10-05", "2026-10-12")],
        )
        weekly = build_weekly_summary(df)
        self.assertEqual(
            list(weekly.index),
            [pd.Timestamp(d) for d in ("2026-09-28", "2026-10-05", "2026-10-12")],
        )
        self.assertEqual(weekly["day_count"].tolist(), [1, 2, 1])

    def test_complete_week_needs_seven_distinct_days(self) -> None:
        dates = [f"2026-10-{day:02d}" for day in range(5, 12)] + ["2026-10-05"]
        df = self._analysis(dates, [1] * 8)
        df = df.assign(shift=pd.array(["morning"] * 7 + ["afternoon"], dtype="string"))
        weekly = build_weekly_summary(df)
        self.assertEqual(len(weekly), 1)
        self.assertEqual(int(weekly["day_count"].iloc[0]), 7)
        self.assertEqual(int(weekly["record_count"].iloc[0]), 8)
        self.assertTrue(bool(weekly["is_complete_week"].iloc[0]))

    def test_plan_met_and_has_downtime_bounds(self) -> None:
        clean_df = _typed(
            [
                (1, "2026-10-01", "morning", "M1", "P-A", 100, 100, 0.0),
                (2, "2026-10-02", "morning", "M1", "P-A", 100, 99, 8.0),
            ]
        )
        df = add_derived_columns(clean_df, self.machine_master, self.product_master)
        self.assertEqual(df["plan_met"].tolist(), [True, False])
        self.assertEqual(df["has_downtime"].tolist(), [False, True])
        self.assertEqual(df["availability_pct"].tolist(), [100.0, 0.0])

    def test_unavailable_machine_uses_master_capacity(self) -> None:
        clean_df = _typed([(1, "2026-10-01", "morning", "M4", "P-C", 1000, 855, 0.0)])
        df = add_derived_columns(clean_df, self.machine_master, self.product_master)
        self.assertAlmostEqual(df["shift_effective_capacity"].iloc[0], 1710.0)
        self.assertAlmostEqual(df["capacity_utilization_pct"].iloc[0], 50.0)


# ---------------------------------------------------------------------------
# Full pipeline on Kişi A's dirty data (Section 7.5 values of derived columns)
# ---------------------------------------------------------------------------

@unittest.skipUnless(REAL_DATA_READY, REAL_DATA_REASON)
class TestFeaturesFullPipeline(unittest.TestCase):
    """Section 7.5 values that depend on the derived columns and series."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()
        raw_df = load_records_dataframe(str(DIRTY_CSV_PATH))
        cls.clean_df, _ = clean_records(raw_df, cls.machine_master, cls.product_master)
        cls.analysis_df = add_derived_columns(cls.clean_df, cls.machine_master, cls.product_master)
        cls.daily = build_daily_series(cls.analysis_df)
        cls.weekly = build_weekly_summary(cls.analysis_df)

    def setUp(self) -> None:
        _strict_warnings(self)

    def test_shape(self) -> None:
        self.assertEqual(self.analysis_df.shape, (546, len(RECORD_COLUMNS) + len(DERIVED_COLUMNS)))
        self.assertFalse(self.analysis_df.isna().any().any())

    def test_overall_values(self) -> None:
        df = self.analysis_df
        self.assertEqual(int(df["production_gap"].sum()), -22513)
        utilization = df["actual_units"].sum() / df["shift_effective_capacity"].sum() * 100
        self.assertAlmostEqual(utilization, 80.72, delta=DELTA)
        self.assertEqual(int(df["has_downtime"].sum()), 159)
        self.assertEqual(int((~df["plan_met"]).sum()), 425)
        self.assertAlmostEqual(df["attainment_pct"].std(ddof=0), 10.12, delta=DELTA)

    def test_capacity_utilization_by_machine(self) -> None:
        grouped = self.analysis_df.groupby("machine_id").agg(
            actual=("actual_units", "sum"), capacity=("shift_effective_capacity", "sum")
        )
        result = (grouped["actual"] / grouped["capacity"] * 100).to_dict()
        for machine, expected in (("M1", 80.68), ("M2", 82.79), ("M3", 77.32), ("M5", 79.13)):
            self.assertAlmostEqual(result[machine], expected, delta=DELTA)

    def test_plan_not_met_share_by_machine(self) -> None:
        share = (~self.analysis_df["plan_met"]).groupby(self.analysis_df["machine_id"]).mean() * 100
        for machine, expected in (("M1", 73.83), ("M2", 76.36), ("M3", 85.32), ("M5", 77.27)):
            self.assertAlmostEqual(share[machine], expected, delta=DELTA)

    def test_attainment_by_downtime_flag(self) -> None:
        means = self.analysis_df.groupby("has_downtime")["attainment_pct"].mean()
        self.assertAlmostEqual(means[True], 80.40, delta=DELTA)
        self.assertAlmostEqual(means[False], 97.05, delta=DELTA)
        self.assertAlmostEqual(means[False] - means[True], 16.65, delta=DELTA)

    def test_daily_series(self) -> None:
        self.assertEqual(len(self.daily), 120)
        self.assertEqual(self.daily.index[0], pd.Timestamp("2026-10-01"))
        self.assertEqual(self.daily.index[-1], pd.Timestamp("2027-01-28"))
        self.assertFalse(self.daily["is_missing_day"].any())
        self.assertEqual(
            self.daily["record_count"].value_counts().to_dict(), {5: 76, 4: 36, 3: 6, 2: 2}
        )
        self.assertEqual(int(self.daily["total_actual_units"].sum()), 270519)
        self.assertEqual(int(self.daily["actual_units_ma7"].isna().sum()), 6)
        expected_ma7 = self.daily["total_actual_units"].iloc[:7].mean()
        self.assertAlmostEqual(self.daily["actual_units_ma7"].iloc[6], expected_ma7)

    def test_weekly_summary(self) -> None:
        weekly = self.weekly
        self.assertEqual(len(weekly), 18)
        self.assertEqual(int(weekly["is_complete_week"].sum()), 16)
        first, last = weekly.iloc[0], weekly.iloc[-1]
        self.assertEqual(weekly.index[0], pd.Timestamp("2026-09-28"))
        self.assertEqual((int(first["day_count"]), int(first["record_count"])), (4, 20))
        self.assertEqual(int(first["production_gap"]), -590)
        self.assertEqual(weekly.index[-1], pd.Timestamp("2027-01-25"))
        self.assertEqual((int(last["day_count"]), int(last["record_count"])), (4, 20))
        self.assertEqual(int(last["production_gap"]), -989)
        self.assertEqual(int(weekly["record_count"].sum()), 546)

    def test_largest_gap_in_complete_weeks(self) -> None:
        complete = self.weekly[self.weekly["is_complete_week"]]
        self.assertEqual(complete["production_gap"].idxmin(), pd.Timestamp("2026-10-19"))
        self.assertEqual(int(complete["production_gap"].min()), -1720)

    def test_inputs_are_not_modified(self) -> None:
        clean_copy = self.clean_df.copy()
        machine_copy, product_copy = self.machine_master.copy(), self.product_master.copy()
        analysis = add_derived_columns(self.clean_df, self.machine_master, self.product_master)
        analysis_copy = analysis.copy()
        build_daily_series(analysis)
        build_weekly_summary(analysis)
        pd.testing.assert_frame_equal(self.clean_df, clean_copy)
        pd.testing.assert_frame_equal(self.machine_master, machine_copy)
        pd.testing.assert_frame_equal(self.product_master, product_copy)
        pd.testing.assert_frame_equal(analysis, analysis_copy)


# ---------------------------------------------------------------------------
# Errors (Section 7.7, features)
# ---------------------------------------------------------------------------

class TestFeatureErrors(unittest.TestCase):
    """Wrong inputs raise TypeError / ValueError with Turkish messages."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.machine_master, cls.product_master = _masters()
        cls.clean_df = _typed([(1, "2026-10-01", "morning", "M1", "P-A", 800, 780, 0.5)])

    def setUp(self) -> None:
        _strict_warnings(self)

    def test_unknown_machine_raises_value_error(self) -> None:
        clean_df = self.clean_df.assign(machine_id=pd.array(["M9"], dtype="string"))
        with self.assertRaisesRegex(ValueError, "karşılığı olmayan machine_id.*M9"):
            add_derived_columns(clean_df, self.machine_master, self.product_master)

    def test_unknown_product_raises_value_error(self) -> None:
        clean_df = self.clean_df.assign(product_code=pd.array(["P-Z"], dtype="string"))
        with self.assertRaisesRegex(ValueError, "karşılığı olmayan product_code.*P-Z"):
            add_derived_columns(clean_df, self.machine_master, self.product_master)

    def test_duplicated_master_key_raises_value_error(self) -> None:
        doubled = pd.concat([self.machine_master, self.machine_master.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "benzersiz değil"):
            add_derived_columns(self.clean_df, doubled, self.product_master)

    def test_empty_frame_raises_value_error(self) -> None:
        empty = self.clean_df.iloc[0:0]
        with self.assertRaisesRegex(ValueError, "boş"):
            add_derived_columns(empty, self.machine_master, self.product_master)
        with self.assertRaisesRegex(ValueError, "boş"):
            build_daily_series(empty)
        with self.assertRaisesRegex(ValueError, "boş"):
            build_weekly_summary(empty.assign(week_start=empty["production_date"]))

    def test_wrong_type_raises_type_error(self) -> None:
        with self.assertRaisesRegex(TypeError, "DataFrame olmalıdır"):
            add_derived_columns([], self.machine_master, self.product_master)
        with self.assertRaises(TypeError):
            add_derived_columns(self.clean_df, {}, self.product_master)
        with self.assertRaises(TypeError):
            build_daily_series([])
        with self.assertRaises(TypeError):
            build_weekly_summary(None)

    def test_text_dates_raise_type_error(self) -> None:
        clean_df = self.clean_df.assign(production_date="2026-10-01")
        with self.assertRaisesRegex(TypeError, "datetime64"):
            add_derived_columns(clean_df, self.machine_master, self.product_master)

    def test_missing_columns_raise_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "shift_effective_capacity"):
            add_derived_columns(
                self.clean_df,
                self.machine_master.drop(columns="shift_effective_capacity"),
                self.product_master,
            )
        with self.assertRaisesRegex(ValueError, "priority"):
            add_derived_columns(
                self.clean_df, self.machine_master, self.product_master.drop(columns="priority")
            )
        with self.assertRaisesRegex(ValueError, "downtime_hours"):
            add_derived_columns(
                self.clean_df.drop(columns="downtime_hours"), self.machine_master, self.product_master
            )
        with self.assertRaisesRegex(ValueError, "week_start"):
            build_weekly_summary(self.clean_df)


class TestFeatureSourceRules(unittest.TestCase):
    """Section 7.6 #7 and Section 10: no row iteration, no copied capacity formula."""

    def setUp(self) -> None:
        self.source = (PROJECT_DIR / "production_analysis" / "features.py").read_text(encoding="utf-8")

    def test_no_row_iteration(self) -> None:
        for pattern in (r"iterrows", r"itertuples", r"\.apply\("):
            self.assertIsNone(re.search(pattern, self.source), pattern)

    def test_no_capacity_formula(self) -> None:
        for pattern in (r"cycle_time_sec", r"working_hours", r"efficiency_pct", r"3600"):
            self.assertIsNone(re.search(pattern, self.source), pattern)

    def test_no_print_or_input(self) -> None:
        self.assertIsNone(re.search(r"\bprint\(|\binput\(", self.source))


if __name__ == "__main__":
    unittest.main()
