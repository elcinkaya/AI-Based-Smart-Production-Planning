"""
test_analysis.py – Unit tests for analysis.py (KPI) and report.py (report text).

Section 7.2 of the project plan (expected KPI values) is referenced by the
plan but is not present in the document. The expected values below are
therefore derived by hand from the raw fields of the 8 fixed test records
(data/test_records.*, Kişi A) and written as explicit arithmetic, so each
value can be checked by reading the test. The report layout test uses the
target report text given in Section 5 of the plan (Kişi C).

KPI tests use in-memory ProductionRecord objects (no files). The data-file
tests only READ data/test_records.json / .csv; nothing in data/ is written.

Author: Kişi C
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import contextlib
import io
import os
import unittest

from production_records.analysis import (
    GROUP_FIELDS,
    SUMMARY_KEYS,
    calculate_attainment_pct,
    calculate_availability_pct,
    calculate_production_gap,
    summarize_by,
    summarize_records,
)
from production_records.record import SHIFT_HOURS, ProductionRecord, Shift
from production_records.report import (
    build_record_table,
    build_summary_report,
    print_summary_report,
)
from production_records.storage import load_records_csv, load_records_json


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# The 8 fixed test records (same values as data/test_records.*):
# (production_date, shift, machine_id, product_code, planned, actual, downtime)
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

# Target report from Section 5 of the plan (8 test records, grouped by machine).
EXPECTED_REPORT_TEXT = "\n".join([
    "==============================================",
    "      ÜRETİM KAYIT PERFORMANS RAPORU",
    "==============================================",
    "Kapsam",
    "  Kayıt sayısı          : 8",
    "  Tarih aralığı         : 2026-10-01 – 2026-10-03",
    "----------------------------------------------",
    "Genel Sonuçlar",
    "  Planlanan üretim      : 4510 adet",
    "  Gerçekleşen üretim    : 4366 adet",
    "  Üretim farkı          : -144 adet",
    "  Plan gerçekleşme      : %96.81",
    "  Toplam duruş          : 5.00 saat",
    "  Kullanılabilirlik     : %92.19",
    "----------------------------------------------",
    "Makine Bazında",
    "  M1 : planlanan 2400, gerçekleşen 2296, fark -104, %95.67",
    "  M2 : planlanan 1130, gerçekleşen 1120, fark -10, %99.12",
    "  M3 : planlanan 980, gerçekleşen 950, fark -30, %96.94",
    "----------------------------------------------",
    "DURUM: PLAN KARŞILANMADI",
    "Üretim açığı: 144 adet",
    "==============================================",
])


def make_test_records() -> list[ProductionRecord]:
    """Return fresh in-memory ProductionRecord objects for the 8 test records."""
    return [
        ProductionRecord(*raw, record_id=idx)
        for idx, raw in enumerate(RAW_TEST_RECORDS, start=1)
    ]


def make_record(day: str = "2026-10-01", shift: str = "morning", machine: str = "M1",
                product: str = "P-A", planned: int = 100, actual: int = 100,
                downtime: float = 0.0) -> ProductionRecord:
    """Return one in-memory record with the given values."""
    return ProductionRecord(day, shift, machine, product, planned, actual, downtime)


# ---------------------------------------------------------------------------
# Single KPI functions
# ---------------------------------------------------------------------------

class TestCalculateProductionGap(unittest.TestCase):
    """calculate_production_gap = actual - planned (sign rule from MP1)."""

    def test_shortfall_is_negative(self) -> None:
        self.assertEqual(calculate_production_gap(800, 780), -20)

    def test_overproduction_is_positive(self) -> None:
        self.assertEqual(calculate_production_gap(500, 530), 30)

    def test_exact_is_zero(self) -> None:
        self.assertEqual(calculate_production_gap(565, 565), 0)

    def test_zero_actual(self) -> None:
        self.assertEqual(calculate_production_gap(320, 0), -320)

    def test_returns_int(self) -> None:
        self.assertIsInstance(calculate_production_gap(800, 780), int)

    def test_wrong_types_raise_type_error(self) -> None:
        for planned, actual in [(800.0, 780), (800, 780.0), ("800", 780),
                                (True, 780), (800, False), (None, 1)]:
            with self.subTest(planned=planned, actual=actual):
                with self.assertRaises(TypeError):
                    calculate_production_gap(planned, actual)

    def test_negative_values_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            calculate_production_gap(-1, 10)
        with self.assertRaises(ValueError):
            calculate_production_gap(10, -1)


class TestCalculateAttainmentPct(unittest.TestCase):
    """calculate_attainment_pct = actual / planned * 100."""

    def test_basic_value(self) -> None:
        self.assertAlmostEqual(calculate_attainment_pct(800, 780), 97.5)

    def test_overproduction_above_100(self) -> None:
        self.assertAlmostEqual(calculate_attainment_pct(500, 530), 106.0)

    def test_exact_is_100(self) -> None:
        self.assertEqual(calculate_attainment_pct(565, 565), 100.0)

    def test_zero_actual_is_0(self) -> None:
        self.assertEqual(calculate_attainment_pct(320, 0), 0.0)

    def test_not_rounded(self) -> None:
        # 2296 / 2400 * 100 = 95.6666...; must not be rounded to 95.67
        value = calculate_attainment_pct(2400, 2296)
        self.assertEqual(value, 2296 / 2400 * 100)
        self.assertNotEqual(value, round(value, 2))

    def test_returns_float(self) -> None:
        self.assertIsInstance(calculate_attainment_pct(800, 800), float)

    def test_planned_zero_or_negative_raises(self) -> None:
        for planned in (0, -5):
            with self.subTest(planned=planned):
                with self.assertRaises(ValueError):
                    calculate_attainment_pct(planned, 10)

    def test_negative_actual_raises(self) -> None:
        with self.assertRaises(ValueError):
            calculate_attainment_pct(100, -1)

    def test_wrong_types_raise_type_error(self) -> None:
        for planned, actual in [(100.0, 50), (100, 50.0), (True, 1), ("100", 50)]:
            with self.subTest(planned=planned, actual=actual):
                with self.assertRaises(TypeError):
                    calculate_attainment_pct(planned, actual)


class TestCalculateAvailabilityPct(unittest.TestCase):
    """calculate_availability_pct = (shift_hours - downtime) / shift_hours * 100."""

    def test_default_shift_is_8_hours(self) -> None:
        self.assertEqual(SHIFT_HOURS, 8.0)
        self.assertAlmostEqual(calculate_availability_pct(0.5), (8 - 0.5) / 8 * 100)

    def test_no_downtime_is_100(self) -> None:
        self.assertEqual(calculate_availability_pct(0.0), 100.0)

    def test_full_downtime_is_0(self) -> None:
        self.assertEqual(calculate_availability_pct(8.0), 0.0)

    def test_multi_record_scheduled_time(self) -> None:
        # 8 records x 8 h = 64 h scheduled, 5 h downtime -> 92.1875 (exact)
        self.assertEqual(calculate_availability_pct(5.0, 8 * SHIFT_HOURS), 92.1875)

    def test_int_inputs_accepted(self) -> None:
        self.assertEqual(calculate_availability_pct(2, 8), 75.0)

    def test_downtime_above_scheduled_raises(self) -> None:
        with self.assertRaises(ValueError):
            calculate_availability_pct(8.25)

    def test_negative_downtime_raises(self) -> None:
        with self.assertRaises(ValueError):
            calculate_availability_pct(-0.5)

    def test_non_positive_shift_hours_raises(self) -> None:
        for hours in (0, -8.0):
            with self.subTest(hours=hours):
                with self.assertRaises(ValueError):
                    calculate_availability_pct(0.0, hours)

    def test_wrong_types_raise_type_error(self) -> None:
        for downtime, hours in [(True, 8.0), ("1", 8.0), (1.0, None), (1.0, False)]:
            with self.subTest(downtime=downtime, hours=hours):
                with self.assertRaises(TypeError):
                    calculate_availability_pct(downtime, hours)


# ---------------------------------------------------------------------------
# summarize_records
# ---------------------------------------------------------------------------

class TestSummarizeRecordsTestData(unittest.TestCase):
    """Summary of the 8 fixed test records (expected values derived by hand)."""

    def setUp(self) -> None:
        self.records = make_test_records()
        self.summary = summarize_records(self.records)
        self.expected_planned = 800 + 800 + 800 + 565 + 565 + 330 + 330 + 320
        self.expected_actual = 780 + 760 + 756 + 560 + 560 + 320 + 320 + 310
        self.expected_downtime = 0.5 + 1.0 + 1.0 + 0.5 + 0.5 + 0.5 + 0.5 + 0.5

    def test_keys_exactly_as_contract(self) -> None:
        self.assertEqual(set(self.summary), set(SUMMARY_KEYS))
        self.assertEqual(len(SUMMARY_KEYS), 11)

    def test_value_types(self) -> None:
        expected_types = {
            "record_count": int, "date_from": str, "date_to": str,
            "total_planned_units": int, "total_actual_units": int,
            "production_gap": int, "attainment_pct": float,
            "total_downtime_hours": float, "availability_pct": float,
            "plan_met": bool, "status_message": str,
        }
        for key, typ in expected_types.items():
            with self.subTest(key=key):
                self.assertIs(type(self.summary[key]), typ)

    def test_scope(self) -> None:
        self.assertEqual(self.summary["record_count"], 8)
        self.assertEqual(self.summary["date_from"], "2026-10-01")
        self.assertEqual(self.summary["date_to"], "2026-10-03")

    def test_totals(self) -> None:
        self.assertEqual(self.summary["total_planned_units"], self.expected_planned)
        self.assertEqual(self.summary["total_actual_units"], self.expected_actual)
        self.assertEqual(self.expected_planned, 4510)
        self.assertEqual(self.expected_actual, 4366)

    def test_production_gap(self) -> None:
        self.assertEqual(self.summary["production_gap"],
                         self.expected_actual - self.expected_planned)
        self.assertEqual(self.summary["production_gap"], -144)

    def test_attainment_pct_unrounded(self) -> None:
        expected = self.expected_actual / self.expected_planned * 100
        self.assertEqual(self.summary["attainment_pct"], expected)
        self.assertEqual(round(self.summary["attainment_pct"], 2), 96.81)
        self.assertNotEqual(self.summary["attainment_pct"], 96.81)

    def test_downtime_and_availability(self) -> None:
        self.assertEqual(self.summary["total_downtime_hours"], self.expected_downtime)
        self.assertEqual(self.summary["total_downtime_hours"], 5.0)
        expected_availability = (8 * 8 - self.expected_downtime) / (8 * 8) * 100
        self.assertEqual(self.summary["availability_pct"], expected_availability)
        self.assertEqual(self.summary["availability_pct"], 92.1875)

    def test_plan_not_met_status(self) -> None:
        self.assertFalse(self.summary["plan_met"])
        self.assertEqual(self.summary["status_message"],
                         "Plan karşılanmadı. Üretim açığı: 144 adet.")

    def test_input_not_modified(self) -> None:
        before = [r.to_dict() for r in self.records]
        summarize_records(self.records)
        self.assertEqual([r.to_dict() for r in self.records], before)

    def test_order_independent(self) -> None:
        reversed_summary = summarize_records(list(reversed(self.records)))
        self.assertEqual(reversed_summary, self.summary)


class TestSummarizeRecordsCases(unittest.TestCase):
    """Status branches, edge cases and invalid input."""

    def test_overproduction_status(self) -> None:
        records = [make_record(planned=500, actual=520),
                   make_record(shift="afternoon", planned=500, actual=510)]
        summary = summarize_records(records)
        self.assertEqual(summary["production_gap"], 30)
        self.assertTrue(summary["plan_met"])
        self.assertEqual(summary["status_message"],
                         "Plan karşılandı. Fazla üretim: 30 adet.")

    def test_exact_status(self) -> None:
        summary = summarize_records([make_record(planned=400, actual=400)])
        self.assertEqual(summary["production_gap"], 0)
        self.assertTrue(summary["plan_met"])
        self.assertEqual(summary["status_message"], "Plan tam olarak gerçekleşti.")

    def test_single_record(self) -> None:
        summary = summarize_records([make_record(planned=800, actual=780, downtime=0.5)])
        self.assertEqual(summary["record_count"], 1)
        self.assertEqual(summary["date_from"], summary["date_to"])
        self.assertEqual(summary["attainment_pct"], 97.5)
        self.assertEqual(summary["availability_pct"], 93.75)

    def test_downtime_is_float_when_all_zero(self) -> None:
        summary = summarize_records([make_record()])
        self.assertIs(type(summary["total_downtime_hours"]), float)
        self.assertEqual(summary["availability_pct"], 100.0)

    def test_empty_list_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            summarize_records([])

    def test_not_a_list_raises_type_error(self) -> None:
        for value in (None, (make_record(),), make_record(), "kayıt"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    summarize_records(value)

    def test_non_record_item_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            summarize_records([make_record(), {"planned_units": 10}])


# ---------------------------------------------------------------------------
# summarize_by
# ---------------------------------------------------------------------------

class TestSummarizeBy(unittest.TestCase):
    """Grouped summaries."""

    def setUp(self) -> None:
        self.records = make_test_records()

    def test_by_machine(self) -> None:
        groups = summarize_by(self.records, "machine_id")
        self.assertEqual(list(groups), ["M1", "M2", "M3"])
        expected = {
            "M1": (800 + 800 + 800, 780 + 760 + 756),
            "M2": (565 + 565, 560 + 560),
            "M3": (330 + 330 + 320, 320 + 320 + 310),
        }
        for machine, (planned, actual) in expected.items():
            with self.subTest(machine=machine):
                group = groups[machine]
                self.assertEqual(group["total_planned_units"], planned)
                self.assertEqual(group["total_actual_units"], actual)
                self.assertEqual(group["production_gap"], actual - planned)
                self.assertEqual(group["attainment_pct"], actual / planned * 100)
        # Rounded values as shown in the Section 5 target report
        self.assertEqual(round(groups["M1"]["attainment_pct"], 2), 95.67)
        self.assertEqual(round(groups["M2"]["attainment_pct"], 2), 99.12)
        self.assertEqual(round(groups["M3"]["attainment_pct"], 2), 96.94)

    def test_by_product(self) -> None:
        groups = summarize_by(self.records, "product_code")
        self.assertEqual(list(groups), ["P-A", "P-B", "P-C"])
        self.assertEqual(groups["P-A"]["total_planned_units"], 800 + 800 + 565)
        self.assertEqual(groups["P-B"]["total_planned_units"], 800 + 565 + 330 + 320)
        self.assertEqual(groups["P-C"]["total_actual_units"], 320)
        self.assertEqual(groups["P-B"]["record_count"], 4)

    def test_by_date(self) -> None:
        groups = summarize_by(self.records, "production_date")
        self.assertEqual(list(groups), ["2026-10-01", "2026-10-02", "2026-10-03"])
        day1 = groups["2026-10-01"]
        self.assertEqual(day1["record_count"], 4)
        self.assertEqual(day1["total_planned_units"], 800 + 565 + 565 + 330)
        self.assertEqual(day1["total_downtime_hours"], 0.5 * 4)
        self.assertEqual(day1["availability_pct"], (4 * 8 - 2.0) / (4 * 8) * 100)

    def test_by_shift_uses_enum_order(self) -> None:
        groups = summarize_by(self.records, "shift")
        self.assertEqual(list(groups), [Shift.MORNING.value, Shift.AFTERNOON.value])
        self.assertEqual(groups["afternoon"]["record_count"], 1)
        self.assertEqual(groups["morning"]["record_count"], 7)

    def test_group_totals_add_up(self) -> None:
        overall = summarize_records(self.records)
        for field in GROUP_FIELDS:
            with self.subTest(field=field):
                groups = summarize_by(self.records, field)
                self.assertEqual(sum(g["record_count"] for g in groups.values()), 8)
                self.assertEqual(sum(g["total_planned_units"] for g in groups.values()),
                                 overall["total_planned_units"])
                self.assertEqual(sum(g["total_actual_units"] for g in groups.values()),
                                 overall["total_actual_units"])
                for group in groups.values():
                    self.assertEqual(set(group), set(SUMMARY_KEYS))

    def test_invalid_group_field_raises_value_error(self) -> None:
        for field in ("record_id", "planned_units", "machine", ""):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    summarize_by(self.records, field)

    def test_non_str_group_field_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            summarize_by(self.records, None)

    def test_empty_records_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            summarize_by([], "machine_id")


# ---------------------------------------------------------------------------
# Data files (read-only) – integration with Kişi A's data and Kişi B's storage
# ---------------------------------------------------------------------------

class TestSummaryFromDataFiles(unittest.TestCase):
    """The test data files give the same KPIs as the in-memory records."""

    def test_json_and_csv_match_in_memory_records(self) -> None:
        expected = summarize_records(make_test_records())
        for loader, name in ((load_records_json, "test_records.json"),
                             (load_records_csv, "test_records.csv")):
            with self.subTest(file=name):
                records = loader(os.path.join(DATA_DIR, name))
                self.assertEqual(records, make_test_records())
                self.assertEqual(summarize_records(records), expected)


# ---------------------------------------------------------------------------
# report.py
# ---------------------------------------------------------------------------

class TestBuildSummaryReport(unittest.TestCase):
    """Report text layout and rounding."""

    def setUp(self) -> None:
        records = make_test_records()
        self.summary = summarize_records(records)
        self.machines = summarize_by(records, "machine_id")

    def test_matches_plan_target_report(self) -> None:
        report = build_summary_report(self.summary, self.machines, "Makine Bazında")
        self.assertEqual(report, EXPECTED_REPORT_TEXT)

    def test_returns_str_and_does_not_print(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            report = build_summary_report(self.summary)
        self.assertIsInstance(report, str)
        self.assertEqual(buffer.getvalue(), "")

    def test_print_summary_report_prints_built_text(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            print_summary_report(self.summary, self.machines, "Makine Bazında")
        self.assertEqual(buffer.getvalue(), EXPECTED_REPORT_TEXT + "\n")

    def test_without_groups_omits_group_section(self) -> None:
        report = build_summary_report(self.summary)
        self.assertNotIn("Makine Bazında", report)
        self.assertNotIn("planlanan 2400", report)
        self.assertEqual(report.count("-" * 46), 2)
        self.assertIn("DURUM: PLAN KARŞILANMADI", report)

    def test_rounding_only_in_report(self) -> None:
        before = dict(self.summary)
        build_summary_report(self.summary, self.machines, "Makine Bazında")
        self.assertEqual(self.summary, before)
        self.assertEqual(self.summary["attainment_pct"], 4366 / 4510 * 100)

    def test_overproduction_status_lines(self) -> None:
        summary = summarize_records([make_record(planned=500, actual=530)])
        lines = build_summary_report(summary).splitlines()
        self.assertEqual(lines[-3:-1], ["DURUM: PLAN KARŞILANDI", "Fazla üretim: 30 adet"])

    def test_exact_status_line(self) -> None:
        summary = summarize_records([make_record(planned=400, actual=400)])
        lines = build_summary_report(summary).splitlines()
        self.assertEqual(lines[-2], "DURUM: PLAN TAM OLARAK GERÇEKLEŞTİ")

    def test_group_keys_are_aligned(self) -> None:
        records = make_test_records()
        report = build_summary_report(
            self.summary, summarize_by(records, "shift"), "Vardiya Bazında")
        self.assertIn("  morning   : planlanan", report)
        self.assertIn("  afternoon : planlanan", report)

    def test_default_group_title(self) -> None:
        report = build_summary_report(self.summary, self.machines)
        self.assertIn("\nGrup Bazında\n", report)

    def test_invalid_summary_raises(self) -> None:
        with self.assertRaises(TypeError):
            build_summary_report(None)
        broken = dict(self.summary)
        del broken["availability_pct"]
        with self.assertRaises(ValueError):
            build_summary_report(broken)
        with self.assertRaises(TypeError):
            build_summary_report(self.summary, ["M1"])


class TestBuildRecordTable(unittest.TestCase):
    """Record listing table used by menu option 2."""

    def test_table_rows(self) -> None:
        table = build_record_table(make_test_records())
        lines = table.splitlines()
        self.assertEqual(len(lines), 2 + 8 + 2)
        self.assertIn("2026-10-01", lines[2])
        self.assertIn("-20", lines[2])      # 780 - 800
        self.assertIn("0.50", lines[2])
        self.assertEqual(lines[-1], "Toplam 8 kayıt listelendi.")

    def test_empty_list(self) -> None:
        self.assertEqual(build_record_table([]), "Gösterilecek kayıt bulunamadı.")

    def test_invalid_input(self) -> None:
        with self.assertRaises(TypeError):
            build_record_table(None)
        with self.assertRaises(TypeError):
            build_record_table([1, 2])


if __name__ == "__main__":
    unittest.main()
