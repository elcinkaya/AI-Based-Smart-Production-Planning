"""
test_schema_masters.py - Unit tests for schema.py and masters.py (Kişi A).

Covers Section 3.2, Section 5 (Stages 1 & 2), Section 7.1, Section 7.6 (#4)
and Section 7.7:
- Schema constants match MP3 CSV_COLUMNS, Shift enum, cleaning issue codes,
  derived columns, and KPI columns.
- build_machine_master(factory) produces exact golden values from Section 7.1
  and matches MP1 scalar capacity functions in a loop (np.allclose).
- build_product_master(factory) produces P-A (30s, 1), P-B (45s, 2), P-C (60s, 3).
- Invalid/corrupt factory arguments raise TypeError or ValueError with Turkish
  messages.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from factory_model import calculations as mp1
from factory_model.serialization import load_factory_json
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.schema import (
    DERIVED_COLUMNS,
    ISSUE_ACTIONS,
    KEY_FIELDS,
    KPI_COLUMNS,
    MACHINE_MASTER_COLUMNS,
    PRODUCT_MASTER_COLUMNS,
    RECORD_COLUMNS,
    SHIFT_HOURS,
    VALID_SHIFTS,
)
from production_records.record import Shift
from production_records.storage import CSV_COLUMNS

SAMPLE_FACTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_factory.json"


class TestSchemaContract(unittest.TestCase):
    """Verify Section 3.2 and Section 5 Stage 1 schema constants."""

    def test_record_columns_match_mp3_csv_columns(self) -> None:
        self.assertEqual(RECORD_COLUMNS, list(CSV_COLUMNS))
        self.assertEqual(
            RECORD_COLUMNS,
            [
                "record_id",
                "production_date",
                "shift",
                "machine_id",
                "product_code",
                "planned_units",
                "actual_units",
                "downtime_hours",
            ],
        )

    def test_valid_shifts_and_key_fields(self) -> None:
        self.assertEqual(VALID_SHIFTS, [s.value for s in Shift])
        self.assertEqual(VALID_SHIFTS, ["morning", "afternoon", "night"])
        self.assertEqual(
            KEY_FIELDS,
            ["production_date", "shift", "machine_id", "product_code", "planned_units"],
        )

    def test_issue_actions_contract(self) -> None:
        expected = {
            "missing_key_field": "dropped",
            "missing_actual_units": "dropped",
            "missing_downtime_hours": "filled",
            "invalid_date": "dropped",
            "invalid_shift": "dropped",
            "unknown_machine_id": "dropped",
            "unknown_product_code": "dropped",
            "invalid_planned_units": "dropped",
            "invalid_actual_units": "dropped",
            "invalid_downtime_hours": "dropped",
            "duplicate_key": "dropped",
        }
        self.assertEqual(ISSUE_ACTIONS, expected)

    def test_derived_and_kpi_columns_contract(self) -> None:
        self.assertEqual(
            DERIVED_COLUMNS,
            [
                "line_id",
                "priority",
                "shift_effective_capacity",
                "production_gap",
                "attainment_pct",
                "availability_pct",
                "capacity_utilization_pct",
                "plan_met",
                "has_downtime",
                "weekday",
                "week_start",
            ],
        )
        self.assertEqual(
            KPI_COLUMNS,
            [
                "record_count",
                "total_planned_units",
                "total_actual_units",
                "production_gap",
                "attainment_pct",
                "total_downtime_hours",
                "availability_pct",
                "capacity_utilization_pct",
                "downtime_event_count",
                "attainment_pct_std",
                "plan_met",
                "status_message",
            ],
        )


class TestMastersGoldenValues(unittest.TestCase):
    """Verify Section 7.1 master tables and Section 7.6 #4 MP1 scalar loop match."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.factory = load_factory_json(str(SAMPLE_FACTORY_PATH))

    def test_machine_master_golden_values(self) -> None:
        df = build_machine_master(self.factory)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), MACHINE_MASTER_COLUMNS)
        self.assertEqual(list(df.index), [0, 1, 2, 3, 4])

        self.assertEqual(df["machine_id"].tolist(), ["M1", "M2", "M3", "M4", "M5"])
        self.assertEqual(df["line_id"].tolist(), ["L1", "L1", "L2", "L2", "L3"])
        self.assertEqual(df["is_available"].tolist(), [True, True, True, False, True])
        self.assertEqual(df["shift_count"].tolist(), [1, 2, 1, 1, 1])

        np.testing.assert_allclose(
            df["theoretical_capacity"].to_numpy(),
            [960.0, 1280.0, 480.0, 1800.0, 960.0],
        )
        np.testing.assert_allclose(
            df["effective_capacity"].to_numpy(),
            [816.0, 1152.0, 336.0, 1710.0, 768.0],
        )
        np.testing.assert_allclose(
            df["shift_effective_capacity"].to_numpy(),
            [816.0, 576.0, 336.0, 1710.0, 768.0],
        )

    def test_machine_master_matches_mp1_scalar_functions(self) -> None:
        df = build_machine_master(self.factory)
        machines = self.factory["machines"]

        theo_loop = [
            mp1.theoretical_capacity(m.working_hours, m.cycle_time_sec) for m in machines
        ]
        eff_loop = [
            mp1.effective_capacity(t, m.efficiency_pct) for t, m in zip(theo_loop, machines)
        ]
        shift_counts = [max(1, round(m.working_hours / SHIFT_HOURS)) for m in machines]
        shift_eff_loop = [e / sc for e, sc in zip(eff_loop, shift_counts)]

        self.assertTrue(np.allclose(df["theoretical_capacity"].to_numpy(), theo_loop))
        self.assertTrue(np.allclose(df["effective_capacity"].to_numpy(), eff_loop))
        self.assertTrue(np.allclose(df["shift_effective_capacity"].to_numpy(), shift_eff_loop))

    def test_product_master_golden_values(self) -> None:
        df = build_product_master(self.factory)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), PRODUCT_MASTER_COLUMNS)
        self.assertEqual(list(df.index), [0, 1, 2])

        self.assertEqual(df["product_code"].tolist(), ["P-A", "P-B", "P-C"])
        self.assertEqual(df["name"].tolist(), ["Bracket", "Shaft", "Housing"])
        np.testing.assert_allclose(df["processing_time_sec"].to_numpy(), [30.0, 45.0, 60.0])
        self.assertEqual(df["priority"].tolist(), [1, 2, 3])

    def test_invalid_factory_inputs_raise_errors(self) -> None:
        with self.assertRaises(TypeError):
            build_machine_master(["not", "a", "dict"])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            build_product_master(None)  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            build_machine_master({})
        with self.assertRaises(ValueError):
            build_product_master({"products": []})

        with self.assertRaises(TypeError):
            build_machine_master({"machines": [{"machine_id": "M1"}]})
        with self.assertRaises(TypeError):
            build_product_master({"products": [{"product_code": "P-A"}]})


if __name__ == "__main__":
    unittest.main()
