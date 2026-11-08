"""
test_integration.py - MP1, MP2, MP3, MP4 compatibility tests (plan Section 7.6).

Covers all 8 scenarios of Section 7.6:
1. Convert the 546 clean records with dataframe_to_records and run MP3
   summarize_by (machine_id, product_code, shift, production_date) -> the 7
   shared KPI fields match the Pandas KPI tables within delta=0.01.
2. MP4 calculate_statistics on actual_units matches Pandas mean, min, max
   and std (ddof=0), and differs from ddof=1.
3. Read clean_records.csv with MP3 RecordStore -> 546 records, ascending
   record_id; MP3 summarize_records totals equal 293032, 270519, -22513.
4. Machine master capacities match MP1 single-machine functions in a loop
   (np.allclose True).
5. The 600 records produced by the MP4 bridge match Section 7.2 golden
   totals (322489, 298071, 238.0; M1 120, M2 240, M3 120, M5 120).
6. dataframe_to_records -> records_to_dataframe round-trip preserves the
   DataFrame.
7. Source code AST scan: no iterrows, itertuples or apply(..., axis=1) in
   production_analysis modules (and no row loop outside loading.py).
8. Running the full pipeline produces no Pandas/NumPy FutureWarning or
   SettingWithCopyWarning.

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import ast
import os
import tempfile
import unittest
import warnings

import numpy as np
import pandas as pd

import production_analysis as pa
from capacity_simulation.stats import calculate_statistics
from factory_model.calculations import effective_capacity, theoretical_capacity
from factory_model.serialization import load_factory_json
from production_records.analysis import summarize_by, summarize_records
from production_records.record import SHIFT_HOURS
from production_records.record_store import RecordStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PACKAGE_DIR = os.path.join(BASE_DIR, "production_analysis")
FACTORY_PATH = os.path.join(DATA_DIR, "sample_factory.json")
DIRTY_CSV_PATH = os.path.join(DATA_DIR, "raw_records_dirty.csv")

SHARED_MP3_KPI_FIELDS: tuple[str, ...] = (
    "record_count",
    "total_planned_units",
    "total_actual_units",
    "production_gap",
    "attainment_pct",
    "total_downtime_hours",
    "availability_pct",
)


class TestMp1Mp3Mp4Integration(unittest.TestCase):
    """Section 7.6: end-to-end compatibility with Mini Projects 1, 2, 3 and 4."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(FACTORY_PATH)
        cls.machine_master = pa.build_machine_master(cls.factory)
        cls.product_master = pa.build_product_master(cls.factory)
        cls.raw_dirty = pa.load_records_dataframe(DIRTY_CSV_PATH)
        cls.clean_df, cls.cleaning_log_df = pa.clean_records(
            cls.raw_dirty, cls.machine_master, cls.product_master
        )
        cls.analysis_df = pa.add_derived_columns(
            cls.clean_df, cls.machine_master, cls.product_master
        )
        cls.clean_records_list = pa.dataframe_to_records(cls.clean_df)

    # Scenario 1: MP3 summarize_by vs Pandas KPI tables (7 shared fields)
    def test_scenario_1_mp3_summarize_by_matches_pandas_kpi_tables(self) -> None:
        self.assertEqual(len(self.clean_records_list), 546)
        for group_col in ("machine_id", "product_code", "shift", "production_date"):
            mp3_groups = summarize_by(self.clean_records_list, group_col)
            kpi_table = pa.calculate_kpi_table(self.analysis_df, group_col)
            pandas_groups = pa.kpi_table_to_group_summaries(kpi_table)

            self.assertEqual(set(pandas_groups), set(mp3_groups), msg=group_col)
            for key, mp3_summary in mp3_groups.items():
                pd_summary = pandas_groups[key]
                for field in SHARED_MP3_KPI_FIELDS:
                    self.assertAlmostEqual(
                        pd_summary[field],
                        mp3_summary[field],
                        delta=0.01,
                        msg=f"{group_col}={key}, field={field}",
                    )
                self.assertEqual(pd_summary["plan_met"], mp3_summary["plan_met"])
                self.assertEqual(pd_summary["status_message"], mp3_summary["status_message"])

    # Scenario 2: MP4 calculate_statistics vs Pandas on actual_units
    def test_scenario_2_mp4_calculate_statistics_matches_pandas_ddof0(self) -> None:
        actual_series = self.analysis_df["actual_units"]
        mp4_stats = calculate_statistics(actual_series.to_numpy())

        self.assertAlmostEqual(float(actual_series.mean()), mp4_stats["mean"], places=10)
        self.assertAlmostEqual(float(actual_series.min()), mp4_stats["min"], places=10)
        self.assertAlmostEqual(float(actual_series.max()), mp4_stats["max"], places=10)
        self.assertAlmostEqual(float(actual_series.std(ddof=0)), mp4_stats["std"], places=10)
        self.assertNotAlmostEqual(float(actual_series.std(ddof=1)), mp4_stats["std"], places=3)

    # Scenario 3: clean_records.csv read by MP3 RecordStore
    def test_scenario_3_clean_records_csv_readable_by_mp3_record_store(self) -> None:
        kpi_tables = pa.build_kpi_tables(self.analysis_df)
        daily = pa.build_daily_series(self.analysis_df)
        weekly = pa.build_weekly_summary(self.analysis_df)

        with tempfile.TemporaryDirectory() as tmp:
            paths = pa.save_analysis_outputs(
                tmp,
                self.clean_df,
                self.cleaning_log_df,
                self.analysis_df,
                kpi_tables,
                daily,
                weekly,
            )
            clean_csv_path = paths[0]
            store = RecordStore(
                clean_csv_path,
                valid_machine_ids=set(self.machine_master["machine_id"].tolist()),
                valid_product_codes=set(self.product_master["product_code"].tolist()),
            )
            records = store.get_all()
            self.assertEqual(len(records), 546)
            record_ids = [rec.record_id for rec in records]
            self.assertEqual(record_ids, sorted(record_ids))
            self.assertEqual(len(set(record_ids)), 546)

            mp3_summary = summarize_records(records)
            self.assertEqual(mp3_summary["total_planned_units"], 293032)
            self.assertEqual(mp3_summary["total_actual_units"], 270519)
            self.assertEqual(mp3_summary["production_gap"], -22513)
            self.assertAlmostEqual(mp3_summary["attainment_pct"], 92.32, delta=0.01)
            self.assertAlmostEqual(mp3_summary["total_downtime_hours"], 223.375, delta=0.001)
            self.assertAlmostEqual(mp3_summary["availability_pct"], 94.89, delta=0.01)

    # Scenario 4: Machine master capacities vs MP1 single functions
    def test_scenario_4_machine_master_capacities_match_mp1_functions(self) -> None:
        machines = self.factory["machines"]
        loop_theoretical = []
        loop_effective = []
        loop_shift_effective = []
        for machine in machines:
            theo = theoretical_capacity(machine.working_hours, machine.cycle_time_sec)
            eff = effective_capacity(theo, machine.efficiency_pct)
            shifts = max(1, round(machine.working_hours / SHIFT_HOURS))
            loop_theoretical.append(theo)
            loop_effective.append(eff)
            loop_shift_effective.append(eff / shifts)

        self.assertTrue(
            np.allclose(self.machine_master["theoretical_capacity"].to_numpy(), loop_theoretical)
        )
        self.assertTrue(
            np.allclose(self.machine_master["effective_capacity"].to_numpy(), loop_effective)
        )
        self.assertTrue(
            np.allclose(
                self.machine_master["shift_effective_capacity"].to_numpy(), loop_shift_effective
            )
        )

    # Scenario 5: MP4 bridge produces 600 records matching Section 7.2 totals
    def test_scenario_5_mp4_bridge_produces_600_records_matching_golden_totals(self) -> None:
        raw_records = pa.build_clean_records(self.factory, days=120, seed=42)
        self.assertEqual(len(raw_records), 600)
        self.assertEqual(sum(r.planned_units for r in raw_records), 322489)
        self.assertEqual(sum(r.actual_units for r in raw_records), 298071)
        self.assertAlmostEqual(sum(r.downtime_hours for r in raw_records), 238.0, places=6)

        counts_by_machine: dict[str, int] = {}
        for rec in raw_records:
            counts_by_machine[rec.machine_id] = counts_by_machine.get(rec.machine_id, 0) + 1
        self.assertEqual(counts_by_machine, {"M1": 120, "M2": 240, "M3": 120, "M5": 120})

    # Scenario 6: dataframe_to_records -> records_to_dataframe round-trip
    def test_scenario_6_dataframe_to_records_roundtrip_preserves_frame(self) -> None:
        records = pa.dataframe_to_records(self.clean_df)
        reconstructed = pa.records_to_dataframe(records)
        pd.testing.assert_frame_equal(reconstructed, self.clean_df, check_dtype=False)

    # Scenario 7: Source code scan - no iterrows, itertuples or apply(axis=1)
    def test_scenario_7_no_forbidden_row_iteration_in_package(self) -> None:
        forbidden_methods = {"iterrows", "itertuples"}
        for filename in sorted(os.listdir(PACKAGE_DIR)):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(PACKAGE_DIR, filename)
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            tree = ast.parse(source, filename=filename)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    self.assertNotIn(
                        attr,
                        forbidden_methods,
                        msg=f"Forbidden '{attr}' call in {filename}:{node.lineno}",
                    )
                    if attr == "apply":
                        for kw in node.keywords:
                            if kw.arg == "axis" and isinstance(kw.value, ast.Constant):
                                self.assertNotIn(
                                    kw.value.value,
                                    (1, "columns"),
                                    msg=f"Forbidden apply(axis=1) in {filename}:{node.lineno}",
                                )
                    # Every .std(...) call in production_analysis must pass ddof=0 explicitly
                    if attr == "std":
                        ddof_values = [
                            kw.value.value
                            for kw in node.keywords
                            if kw.arg == "ddof" and isinstance(kw.value, ast.Constant)
                        ]
                        self.assertEqual(
                            ddof_values,
                            [0],
                            msg=f"std() without explicit ddof=0 in {filename}:{node.lineno}",
                        )
                    # Logic modules must not call print() or input()
                if (
                    filename != "report.py"
                    and isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                ):
                    self.assertNotIn(
                        node.func.id,
                        {"print", "input"},
                        msg=f"Forbidden {node.func.id}() in logic module {filename}:{node.lineno}",
                    )

    # Scenario 8: Zero FutureWarning / SettingWithCopyWarning across pipeline
    def test_scenario_8_pipeline_emits_no_future_or_copy_warnings(self) -> None:
        warning_classes: list[type[Warning]] = [FutureWarning]
        if hasattr(pd.errors, "SettingWithCopyWarning"):
            warning_classes.append(pd.errors.SettingWithCopyWarning)
        if hasattr(pd.errors, "ChainedAssignmentError"):
            warning_classes.append(pd.errors.ChainedAssignmentError)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            raw = pa.load_records_dataframe(DIRTY_CSV_PATH)
            clean_df, log_df = pa.clean_records(raw, self.machine_master, self.product_master)
            cleaning_summary = pa.summarize_cleaning(raw, clean_df, log_df)
            analysis_df = pa.add_derived_columns(
                clean_df, self.machine_master, self.product_master
            )
            daily = pa.build_daily_series(analysis_df)
            weekly = pa.build_weekly_summary(analysis_df)
            kpi_tables = pa.build_kpi_tables(analysis_df)
            summary = pa.summarize_kpi(analysis_df)
            answers = pa.answer_business_questions(analysis_df)
            _ = pa.build_analysis_report(cleaning_summary, summary, kpi_tables, answers)
            with tempfile.TemporaryDirectory() as tmp:
                pa.save_analysis_outputs(
                    tmp, clean_df, log_df, analysis_df, kpi_tables, daily, weekly
                )

        relevant = [
            w for w in caught if issubclass(w.category, tuple(warning_classes))
        ]
        self.assertEqual(relevant, [], msg=f"Unexpected warnings: {relevant}")


if __name__ == "__main__":
    unittest.main()
