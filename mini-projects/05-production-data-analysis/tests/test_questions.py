"""
test_questions.py - Business question and report tests (plan 7.5 and 7.7).

Covers:
- Section 7.5: golden answers for q1 ... q7 on the 546 clean records.
- Non-hardcoded verification: changing the input DataFrame changes the
  returned answers accordingly; partial-week edge case (q5 when no complete
  week exists); single-group downtime edge case (q7).
- build_analysis_report and save_analysis_outputs (Section 4 CSV outputs,
  MP3 format and Section 7.7 invalid inputs).

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import os
import tempfile
import unittest

import pandas as pd

from factory_model.serialization import load_factory_json
from production_analysis.cleaning import clean_records, summarize_cleaning
from production_analysis.features import (
    add_derived_columns,
    build_daily_series,
    build_weekly_summary,
)
from production_analysis.kpi import build_kpi_tables, summarize_kpi
from production_analysis.loading import load_records_dataframe
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.questions import QUESTIONS, answer_business_questions
from production_analysis.report import (
    build_analysis_report,
    save_analysis_outputs,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTORY_PATH = os.path.join(DATA_DIR, "sample_factory.json")
TEST_RECORDS_PATH = os.path.join(DATA_DIR, "test_records.csv")
DIRTY_CSV_PATH = os.path.join(DATA_DIR, "raw_records_dirty.csv")


class _QuestionFixtures(unittest.TestCase):
    """Shared fixtures loaded once per test class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(FACTORY_PATH)
        cls.machine_master = build_machine_master(cls.factory)
        cls.product_master = build_product_master(cls.factory)

        raw_dirty = load_records_dataframe(DIRTY_CSV_PATH)
        cls.clean_df, cls.cleaning_log_df = clean_records(
            raw_dirty, cls.machine_master, cls.product_master
        )
        cls.cleaning_summary = summarize_cleaning(raw_dirty, cls.clean_df, cls.cleaning_log_df)
        cls.analysis_df = add_derived_columns(
            cls.clean_df, cls.machine_master, cls.product_master
        )
        cls.answers = answer_business_questions(cls.analysis_df)


# ---------------------------------------------------------------------------
# Section 7.5 - Business questions golden values
# ---------------------------------------------------------------------------

class TestBusinessQuestionsGoldenValues(_QuestionFixtures):
    """Section 7.5: q1 ... q7 golden answers on the 546 clean records."""

    def test_structure_and_turkish_question_texts(self) -> None:
        self.assertEqual(list(self.answers), list(QUESTIONS))
        for key, text in QUESTIONS.items():
            self.assertEqual(self.answers[key]["question"], text)
            self.assertIsInstance(self.answers[key]["answer"], dict)

    def test_q1_lowest_plan_attainment_machine(self) -> None:
        a1 = self.answers["q1"]["answer"]
        self.assertEqual(a1["machine_id"], "M3")
        self.assertAlmostEqual(a1["attainment_pct"], 90.23, delta=0.01)
        self.assertAlmostEqual(a1["values"]["M1"], 92.82, delta=0.01)
        self.assertAlmostEqual(a1["values"]["M2"], 93.72, delta=0.01)
        self.assertAlmostEqual(a1["values"]["M3"], 90.23, delta=0.01)
        self.assertAlmostEqual(a1["values"]["M5"], 90.56, delta=0.01)

    def test_q2_lowest_availability_shift(self) -> None:
        a2 = self.answers["q2"]["answer"]
        self.assertEqual(a2["shift"], "morning")
        self.assertAlmostEqual(a2["availability_pct"], 94.51, delta=0.01)
        self.assertAlmostEqual(a2["values"]["afternoon"], 96.43, delta=0.01)

    def test_q3_total_vs_per_record_downtime_by_product(self) -> None:
        a3 = self.answers["q3"]["answer"]
        self.assertEqual(a3["total_product_code"], "P-B")
        self.assertAlmostEqual(a3["total_downtime_hours"], 83.875, delta=0.001)
        self.assertEqual(a3["mean_product_code"], "P-C")
        self.assertAlmostEqual(a3["mean_downtime_hours"], 0.4956, delta=0.001)
        self.assertAlmostEqual(a3["mean_values"]["P-A"], 0.3795, delta=0.001)
        self.assertAlmostEqual(a3["mean_values"]["P-B"], 0.3938, delta=0.001)

    def test_q4_missed_plan_share_and_worst_machine(self) -> None:
        a4 = self.answers["q4"]["answer"]
        self.assertEqual(a4["missed_count"], 425)
        self.assertEqual(a4["record_count"], 546)
        self.assertAlmostEqual(a4["missed_pct"], 77.84, delta=0.01)
        self.assertEqual(a4["machine_id"], "M3")
        self.assertAlmostEqual(a4["machine_missed_pct"], 85.32, delta=0.01)
        self.assertAlmostEqual(a4["values"]["M1"], 73.83, delta=0.01)
        self.assertAlmostEqual(a4["values"]["M2"], 76.36, delta=0.01)
        self.assertAlmostEqual(a4["values"]["M5"], 77.27, delta=0.01)

    def test_q5_largest_shortfall_complete_week(self) -> None:
        a5 = self.answers["q5"]["answer"]
        self.assertEqual(a5["week_count"], 18)
        self.assertEqual(a5["complete_week_count"], 16)
        self.assertEqual(a5["week_start"], "2026-10-19")
        self.assertEqual(a5["production_gap"], -1720)

    def test_q6_highest_capacity_utilization_machine(self) -> None:
        a6 = self.answers["q6"]["answer"]
        self.assertEqual(a6["machine_id"], "M2")
        self.assertAlmostEqual(a6["capacity_utilization_pct"], 82.79, delta=0.01)
        self.assertAlmostEqual(a6["values"]["M1"], 80.68, delta=0.01)
        self.assertAlmostEqual(a6["values"]["M5"], 79.13, delta=0.01)
        self.assertAlmostEqual(a6["values"]["M3"], 77.32, delta=0.01)

    def test_q7_downtime_vs_no_downtime_mean_attainment_difference(self) -> None:
        a7 = self.answers["q7"]["answer"]
        self.assertEqual(a7["with_downtime_count"], 159)
        self.assertEqual(a7["without_downtime_count"], 387)
        self.assertAlmostEqual(a7["with_downtime_mean_attainment_pct"], 80.40, delta=0.01)
        self.assertAlmostEqual(a7["without_downtime_mean_attainment_pct"], 97.05, delta=0.01)
        self.assertAlmostEqual(a7["difference_pct_points"], 16.65, delta=0.01)


# ---------------------------------------------------------------------------
# Dynamic / non-hardcoded & report tests
# ---------------------------------------------------------------------------

class TestQuestionsDynamicAndReport(_QuestionFixtures):
    """Verify answers are dynamically computed and report/export functions work."""

    def test_answers_respond_to_modified_data_and_partial_weeks(self) -> None:
        raw_fixed = load_records_dataframe(TEST_RECORDS_PATH)
        clean_fixed, _ = clean_records(raw_fixed, self.machine_master, self.product_master)
        fixed_analysis = add_derived_columns(
            clean_fixed, self.machine_master, self.product_master
        )
        answers = answer_business_questions(fixed_analysis)
        # 8 fixed records span only 3 days -> 0 complete weeks
        self.assertEqual(answers["q5"]["answer"]["complete_week_count"], 0)
        self.assertIsNone(answers["q5"]["answer"]["week_start"])
        self.assertEqual(answers["q1"]["answer"]["machine_id"], "M1")
        self.assertEqual(answers["q6"]["answer"]["machine_id"], "M2")
        # All 8 fixed records have downtime_hours > 0
        self.assertEqual(answers["q7"]["answer"]["without_downtime_count"], 0)
        self.assertIsNone(answers["q7"]["answer"]["difference_pct_points"])

    def test_build_analysis_report_and_save_outputs_in_tempdir(self) -> None:
        kpi_tables = build_kpi_tables(self.analysis_df)
        summary = summarize_kpi(self.analysis_df)
        report_text = build_analysis_report(
            self.cleaning_summary, summary, kpi_tables, self.answers
        )
        self.assertIn("ÜRETİM VERİSİ ANALİZ RAPORU (PANDAS)", report_text)
        self.assertIn("ÜRETİM KAYIT PERFORMANS RAPORU", report_text)
        self.assertIn("293032 adet", report_text)
        self.assertIn("week_start 2026-10-19, -1720 adet", report_text)
        self.assertIn("P-B toplamda önde, ancak kayıt başına P-C daha kötü", report_text)

        daily = build_daily_series(self.analysis_df)
        weekly = build_weekly_summary(self.analysis_df)
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_analysis_outputs(
                tmp,
                self.clean_df,
                self.cleaning_log_df,
                self.analysis_df,
                kpi_tables,
                daily,
                weekly,
            )
            self.assertEqual(len(paths), 10)
            for path in paths:
                self.assertTrue(os.path.isfile(path), msg=path)
                self.assertGreater(os.path.getsize(path), 0, msg=path)

    def test_invalid_inputs_raise_errors(self) -> None:
        with self.assertRaises(TypeError):
            answer_business_questions("invalid")
        with self.assertRaises(ValueError):
            answer_business_questions(self.analysis_df.iloc[0:0].copy())
        with self.assertRaises(ValueError):
            answer_business_questions(self.analysis_df.drop(columns=["week_start"]))

        kpi_tables = build_kpi_tables(self.analysis_df)
        daily = build_daily_series(self.analysis_df)
        weekly = build_weekly_summary(self.analysis_df)
        with self.assertRaises(TypeError):
            save_analysis_outputs(
                123,
                self.clean_df,
                self.cleaning_log_df,
                self.analysis_df,
                kpi_tables,
                daily,
                weekly,
            )
        with self.assertRaises(ValueError):
            save_analysis_outputs(
                "   ",
                self.clean_df,
                self.cleaning_log_df,
                self.analysis_df,
                kpi_tables,
                daily,
                weekly,
            )
        with tempfile.TemporaryDirectory() as tmp:
            blocked_file = os.path.join(tmp, "not_a_dir")
            with open(blocked_file, "w", encoding="utf-8") as handle:
                handle.write("x")
            with self.assertRaises(ValueError):
                save_analysis_outputs(
                    blocked_file,
                    self.clean_df,
                    self.cleaning_log_df,
                    self.analysis_df,
                    kpi_tables,
                    daily,
                    weekly,
                )


if __name__ == "__main__":
    unittest.main()
