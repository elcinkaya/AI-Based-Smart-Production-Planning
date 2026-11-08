"""
test_kpi.py - Unit and golden tests of production_analysis.kpi (plan 7.4, 7.5, 7.7).

Covers:
- Section 7.4: MP3 8 fixed records (test_records.csv) - overall summary,
  machine, product, shift and day KPI tables, capacity_utilization_pct
  (overall 94.75; M1 93.79, M2 97.22, M3 94.25), ddof=0 vs ddof=1 standard
  deviation, unrounded numbers, status messages.
- Section 7.5: 546 clean records - summarize_kpi golden values, machine /
  product / shift / day / week KPI tables, group total invariants.
- kpi_table_to_group_summaries + MP3 build_summary_report compatibility.
- Multi-column group_by, input immutability, Section 7.7 invalid inputs.

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import os
import unittest

import numpy as np
import pandas as pd

from factory_model.serialization import load_factory_json
from production_analysis.cleaning import clean_records
from production_analysis.features import add_derived_columns
from production_analysis.kpi import (
    ALL_GROUP_LABEL,
    EXTRA_SUMMARY_KEYS,
    KPI_TABLE_GROUPS,
    build_kpi_tables,
    calculate_group_date_ranges,
    calculate_kpi_table,
    kpi_table_to_group_summaries,
    summarize_kpi,
)
from production_analysis.loading import load_records_dataframe
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.schema import KPI_COLUMNS
from production_records.analysis import SUMMARY_KEYS, summarize_by, summarize_records
from production_records.report import build_summary_report
from production_records.storage import load_records_csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTORY_PATH = os.path.join(DATA_DIR, "sample_factory.json")
TEST_RECORDS_PATH = os.path.join(DATA_DIR, "test_records.csv")
DIRTY_CSV_PATH = os.path.join(DATA_DIR, "raw_records_dirty.csv")


class _KpiFixtures(unittest.TestCase):
    """Shared fixtures loaded once per test class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(FACTORY_PATH)
        cls.machine_master = build_machine_master(cls.factory)
        cls.product_master = build_product_master(cls.factory)

        # MP3 8 fixed records
        raw_fixed = load_records_dataframe(TEST_RECORDS_PATH)
        clean_fixed, _ = clean_records(raw_fixed, cls.machine_master, cls.product_master)
        cls.fixed_analysis = add_derived_columns(
            clean_fixed, cls.machine_master, cls.product_master
        )
        cls.mp3_fixed_records = load_records_csv(TEST_RECORDS_PATH)

        # Full pipeline (610 dirty -> 546 clean)
        raw_dirty = load_records_dataframe(DIRTY_CSV_PATH)
        cls.clean_df, cls.cleaning_log_df = clean_records(
            raw_dirty, cls.machine_master, cls.product_master
        )
        cls.analysis_df = add_derived_columns(
            cls.clean_df, cls.machine_master, cls.product_master
        )


# ---------------------------------------------------------------------------
# Section 7.4 - MP3 8 fixed records
# ---------------------------------------------------------------------------

class TestFixedRecordsKpi(_KpiFixtures):
    """Section 7.4: KPI tables on the 8 fixed records of MP3."""

    def test_overall_summary_matches_mp3_golden_values(self) -> None:
        summary = summarize_kpi(self.fixed_analysis)
        mp3_summary = summarize_records(self.mp3_fixed_records)

        for key in SUMMARY_KEYS:
            self.assertIn(key, summary)
            if isinstance(mp3_summary[key], float):
                self.assertAlmostEqual(summary[key], mp3_summary[key], places=10)
            else:
                self.assertEqual(summary[key], mp3_summary[key])

        self.assertEqual(summary["record_count"], 8)
        self.assertEqual(summary["date_from"], "2026-10-01")
        self.assertEqual(summary["date_to"], "2026-10-03")
        self.assertEqual(summary["total_planned_units"], 4510)
        self.assertEqual(summary["total_actual_units"], 4366)
        self.assertEqual(summary["production_gap"], -144)
        self.assertAlmostEqual(summary["attainment_pct"], 96.81, delta=0.01)
        self.assertNotEqual(summary["attainment_pct"], 96.81)  # not rounded
        self.assertAlmostEqual(summary["total_downtime_hours"], 5.0, delta=0.01)
        self.assertAlmostEqual(summary["availability_pct"], 92.19, delta=0.01)
        self.assertFalse(summary["plan_met"])
        self.assertEqual(
            summary["status_message"], "Plan karşılanmadı. Üretim açığı: 144 adet."
        )
        # MP5 extra keys (4366 / 4608 * 100 = 94.74826...)
        self.assertAlmostEqual(summary["capacity_utilization_pct"], 4366 / 4608 * 100, places=9)
        self.assertAlmostEqual(summary["capacity_utilization_pct"], 94.75, delta=0.01)
        self.assertEqual(summary["downtime_event_count"], 8)

    def test_group_by_none_returns_single_all_row(self) -> None:
        table = calculate_kpi_table(self.fixed_analysis, group_by=None)
        self.assertEqual(list(table.columns), KPI_COLUMNS)
        self.assertEqual(list(table.index), [ALL_GROUP_LABEL])
        row = table.loc[ALL_GROUP_LABEL]
        self.assertEqual(int(row["total_planned_units"]), 4510)
        self.assertEqual(int(row["total_actual_units"]), 4366)
        self.assertAlmostEqual(float(row["capacity_utilization_pct"]), 94.75, delta=0.01)

    def test_machine_kpi_table_and_capacity_utilization(self) -> None:
        table = calculate_kpi_table(self.fixed_analysis, "machine_id")
        self.assertEqual(list(table.index), ["M1", "M2", "M3"])
        self.assertAlmostEqual(float(table.loc["M1", "capacity_utilization_pct"]), 93.79, delta=0.01)
        self.assertAlmostEqual(float(table.loc["M2", "capacity_utilization_pct"]), 97.22, delta=0.01)
        self.assertAlmostEqual(float(table.loc["M3", "capacity_utilization_pct"]), 94.25, delta=0.01)

        mp3_by_machine = summarize_by(self.mp3_fixed_records, "machine_id")
        for machine_id, mp3_group in mp3_by_machine.items():
            row = table.loc[machine_id]
            self.assertEqual(int(row["record_count"]), mp3_group["record_count"])
            self.assertEqual(int(row["total_planned_units"]), mp3_group["total_planned_units"])
            self.assertEqual(int(row["total_actual_units"]), mp3_group["total_actual_units"])
            self.assertEqual(int(row["production_gap"]), mp3_group["production_gap"])
            self.assertAlmostEqual(float(row["attainment_pct"]), mp3_group["attainment_pct"], delta=0.01)
            self.assertAlmostEqual(
                float(row["total_downtime_hours"]), mp3_group["total_downtime_hours"], delta=0.01
            )
            self.assertAlmostEqual(
                float(row["availability_pct"]), mp3_group["availability_pct"], delta=0.01
            )

    def test_ddof_zero_enforced_and_distinct_from_ddof_one(self) -> None:
        table = calculate_kpi_table(self.fixed_analysis, "machine_id")
        m1_values = self.fixed_analysis.loc[
            self.fixed_analysis["machine_id"] == "M1", "attainment_pct"
        ]
        std_ddof0 = float(np.std(m1_values.to_numpy(), ddof=0))
        std_ddof1 = float(m1_values.std(ddof=1))
        self.assertAlmostEqual(float(table.loc["M1", "attainment_pct_std"]), std_ddof0, places=10)
        self.assertNotAlmostEqual(float(table.loc["M1", "attainment_pct_std"]), std_ddof1, places=3)

        # Also verify the Section 7.4 golden discrimination (6.06 for ddof=0 vs 7.42 for ddof=1)
        synthetic = self.fixed_analysis.copy()
        synthetic.loc[synthetic["machine_id"] == "M1", "attainment_pct"] = [97.50, 102.00, 87.50]
        syn_table = calculate_kpi_table(synthetic, "machine_id")
        self.assertAlmostEqual(float(syn_table.loc["M1", "attainment_pct_std"]), 6.06, delta=0.01)
        self.assertNotAlmostEqual(float(syn_table.loc["M1", "attainment_pct_std"]), 7.42, delta=0.5)

    def test_product_shift_and_day_tables_match_mp3(self) -> None:
        for group_col in ("product_code", "shift", "production_date"):
            table = calculate_kpi_table(self.fixed_analysis, group_col)
            mp3_groups = summarize_by(self.mp3_fixed_records, group_col)
            summaries = kpi_table_to_group_summaries(
                table, calculate_group_date_ranges(self.fixed_analysis, group_col)
            )
            self.assertEqual(set(summaries), set(mp3_groups))
            for key, mp3_group in mp3_groups.items():
                for field in SUMMARY_KEYS:
                    if isinstance(mp3_group[field], float):
                        self.assertAlmostEqual(summaries[key][field], mp3_group[field], delta=0.01)
                    else:
                        self.assertEqual(summaries[key][field], mp3_group[field])


# ---------------------------------------------------------------------------
# Section 7.5 - Full pipeline golden values (546 clean records)
# ---------------------------------------------------------------------------

class TestFullPipelineKpiGoldenValues(_KpiFixtures):
    """Section 7.5: golden KPI values on the 546 clean records."""

    def test_summarize_kpi_golden_values(self) -> None:
        summary = summarize_kpi(self.analysis_df)
        self.assertEqual(summary["record_count"], 546)
        self.assertEqual(summary["date_from"], "2026-10-01")
        self.assertEqual(summary["date_to"], "2027-01-28")
        self.assertEqual(summary["total_planned_units"], 293032)
        self.assertEqual(summary["total_actual_units"], 270519)
        self.assertEqual(summary["production_gap"], -22513)
        self.assertAlmostEqual(summary["attainment_pct"], 92.32, delta=0.01)
        self.assertAlmostEqual(summary["total_downtime_hours"], 223.375, delta=0.001)
        self.assertAlmostEqual(summary["availability_pct"], 94.89, delta=0.01)
        self.assertAlmostEqual(summary["capacity_utilization_pct"], 80.72, delta=0.01)
        self.assertEqual(summary["downtime_event_count"], 159)
        self.assertAlmostEqual(summary["attainment_pct_std"], 10.12, delta=0.01)
        self.assertFalse(summary["plan_met"])
        self.assertEqual(
            summary["status_message"], "Plan karşılanmadı. Üretim açığı: 22513 adet."
        )
        for key in SUMMARY_KEYS + EXTRA_SUMMARY_KEYS:
            self.assertIn(key, summary)

    def test_machine_kpi_table_golden_values(self) -> None:
        table = calculate_kpi_table(self.analysis_df, "machine_id")
        expected = {
            "M1": (107, 75892, 70442, -5450, 92.82, 41.25, 95.18, 80.68, 27, 10.20),
            "M2": (220, 111936, 104909, -7027, 93.72, 63.375, 96.40, 82.79, 67, 7.58),
            "M3": (109, 31382, 28317, -3065, 90.23, 63.25, 92.75, 77.32, 34, 11.69),
            "M5": (110, 73822, 66851, -6971, 90.56, 55.5, 93.69, 79.13, 31, 12.04),
        }
        self.assertEqual(list(table.index), ["M1", "M2", "M3", "M5"])
        for machine_id, vals in expected.items():
            row = table.loc[machine_id]
            self.assertEqual(int(row["record_count"]), vals[0])
            self.assertEqual(int(row["total_planned_units"]), vals[1])
            self.assertEqual(int(row["total_actual_units"]), vals[2])
            self.assertEqual(int(row["production_gap"]), vals[3])
            self.assertAlmostEqual(float(row["attainment_pct"]), vals[4], delta=0.01)
            self.assertAlmostEqual(float(row["total_downtime_hours"]), vals[5], delta=0.001)
            self.assertAlmostEqual(float(row["availability_pct"]), vals[6], delta=0.01)
            self.assertAlmostEqual(float(row["capacity_utilization_pct"]), vals[7], delta=0.01)
            self.assertEqual(int(row["downtime_event_count"]), vals[8])
            self.assertAlmostEqual(float(row["attainment_pct_std"]), vals[9], delta=0.01)
            self.assertFalse(bool(row["plan_met"]))

    def test_product_kpi_table_golden_values(self) -> None:
        table = calculate_kpi_table(self.analysis_df, "product_code")
        expected = {
            "P-A": (220, 131311, 121756, -9555, 92.72, 83.5, 95.26, 80.99, 69, 9.05),
            "P-B": (213, 107065, 99582, -7483, 93.01, 83.875, 95.08, 81.49, 60, 9.97),
            "P-C": (113, 54656, 49181, -5475, 89.98, 56.0, 93.81, 78.57, 30, 12.01),
        }
        self.assertEqual(list(table.index), ["P-A", "P-B", "P-C"])
        for product_code, vals in expected.items():
            row = table.loc[product_code]
            self.assertEqual(int(row["record_count"]), vals[0])
            self.assertEqual(int(row["total_planned_units"]), vals[1])
            self.assertEqual(int(row["total_actual_units"]), vals[2])
            self.assertEqual(int(row["production_gap"]), vals[3])
            self.assertAlmostEqual(float(row["attainment_pct"]), vals[4], delta=0.01)
            self.assertAlmostEqual(float(row["total_downtime_hours"]), vals[5], delta=0.001)
            self.assertAlmostEqual(float(row["availability_pct"]), vals[6], delta=0.01)
            self.assertAlmostEqual(float(row["capacity_utilization_pct"]), vals[7], delta=0.01)
            self.assertEqual(int(row["downtime_event_count"]), vals[8])
            self.assertAlmostEqual(float(row["attainment_pct_std"]), vals[9], delta=0.01)

    def test_shift_kpi_table_golden_values(self) -> None:
        table = calculate_kpi_table(self.analysis_df, "shift")
        expected = {
            "afternoon": (108, 55052, 51631, -3421, 93.79, 30.875, 96.43, 83.00, 32, 7.56),
            "morning": (438, 237980, 218888, -19092, 91.98, 192.5, 94.51, 80.20, 127, 10.62),
        }
        self.assertEqual(list(table.index), ["afternoon", "morning"])
        for shift, vals in expected.items():
            row = table.loc[shift]
            self.assertEqual(int(row["record_count"]), vals[0])
            self.assertEqual(int(row["total_planned_units"]), vals[1])
            self.assertEqual(int(row["total_actual_units"]), vals[2])
            self.assertEqual(int(row["production_gap"]), vals[3])
            self.assertAlmostEqual(float(row["attainment_pct"]), vals[4], delta=0.01)
            self.assertAlmostEqual(float(row["total_downtime_hours"]), vals[5], delta=0.001)
            self.assertAlmostEqual(float(row["availability_pct"]), vals[6], delta=0.01)
            self.assertAlmostEqual(float(row["capacity_utilization_pct"]), vals[7], delta=0.01)
            self.assertEqual(int(row["downtime_event_count"]), vals[8])
            self.assertAlmostEqual(float(row["attainment_pct_std"]), vals[9], delta=0.01)

    def test_all_five_kpi_tables_preserve_overall_totals(self) -> None:
        tables = build_kpi_tables(self.analysis_df)
        self.assertEqual(set(tables), set(KPI_TABLE_GROUPS))
        self.assertEqual(len(tables["day"]), 120)
        self.assertEqual(len(tables["week"]), 18)

        for key, table in tables.items():
            self.assertEqual(list(table.columns), KPI_COLUMNS, msg=key)
            self.assertEqual(int(table["record_count"].sum()), 546, msg=key)
            self.assertEqual(int(table["total_planned_units"].sum()), 293032, msg=key)
            self.assertEqual(int(table["total_actual_units"].sum()), 270519, msg=key)
            self.assertEqual(int(table["production_gap"].sum()), -22513, msg=key)
            self.assertAlmostEqual(
                float(table["total_downtime_hours"].sum()), 223.375, delta=0.001, msg=key
            )
            self.assertEqual(int(table["downtime_event_count"].sum()), 159, msg=key)

    def test_multi_column_group_by_and_mp3_report_compatibility(self) -> None:
        multi = calculate_kpi_table(self.analysis_df, ["machine_id", "shift"])
        self.assertIsInstance(multi.index, pd.MultiIndex)
        self.assertEqual(int(multi["record_count"].sum()), 546)

        summary = summarize_kpi(self.analysis_df)
        machine_groups = kpi_table_to_group_summaries(
            calculate_kpi_table(self.analysis_df, "machine_id")
        )
        report_text = build_summary_report(summary, machine_groups, "Makine Bazında")
        self.assertIn("293032 adet", report_text)
        self.assertIn("270519 adet", report_text)
        self.assertIn("DURUM: PLAN KARŞILANMADI", report_text)

    def test_input_dataframe_not_modified(self) -> None:
        before = self.analysis_df.copy(deep=True)
        _ = calculate_kpi_table(self.analysis_df, "machine_id")
        _ = summarize_kpi(self.analysis_df)
        pd.testing.assert_frame_equal(self.analysis_df, before)


# ---------------------------------------------------------------------------
# Section 7.7 - Invalid / inappropriate inputs
# ---------------------------------------------------------------------------

class TestKpiInvalidInputs(_KpiFixtures):
    """Section 7.7: ValueError / TypeError with Turkish messages on invalid KPI inputs."""

    def test_non_dataframe_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            calculate_kpi_table([1, 2, 3])
        with self.assertRaises(TypeError):
            summarize_kpi("not a dataframe")
        with self.assertRaises(TypeError):
            kpi_table_to_group_summaries({})

    def test_empty_dataframe_raises_value_error(self) -> None:
        empty = self.analysis_df.iloc[0:0].copy()
        with self.assertRaises(ValueError):
            calculate_kpi_table(empty)
        with self.assertRaises(ValueError):
            summarize_kpi(empty)

    def test_unknown_or_invalid_group_by_raises(self) -> None:
        with self.assertRaises(ValueError):
            calculate_kpi_table(self.analysis_df, "unknown_column")
        with self.assertRaises(ValueError):
            calculate_kpi_table(self.analysis_df, [])
        with self.assertRaises(ValueError):
            calculate_kpi_table(self.analysis_df, ["machine_id", "machine_id"])
        with self.assertRaises(TypeError):
            calculate_kpi_table(self.analysis_df, 123)
        with self.assertRaises(TypeError):
            calculate_kpi_table(self.analysis_df, [123])

    def test_missing_required_column_raises_value_error(self) -> None:
        broken = self.analysis_df.drop(columns=["shift_effective_capacity"])
        with self.assertRaises(ValueError):
            calculate_kpi_table(broken)
        broken_kpi = calculate_kpi_table(self.analysis_df, "machine_id").drop(columns=["plan_met"])
        with self.assertRaises(ValueError):
            kpi_table_to_group_summaries(broken_kpi)


if __name__ == "__main__":
    unittest.main()
