"""
test_export.py - Unit tests for export.py (.npz, CSV, split_units).

Covers Section 7.4 (scenarios 2, 11, 12) and Section 7.5 (corrupt/incomplete
files and invalid arguments).  Uses tempfile.TemporaryDirectory() so the
real data/ directory is never modified during tests (Section 3.6).

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from capacity_simulation.export import (
    CSV_COLUMNS,
    load_simulation_npz,
    save_simulation_csv,
    save_simulation_npz,
    split_units,
)
from capacity_simulation.generation import simulate
from capacity_simulation.models import SimulationConfig
from factory_model.serialization import load_factory_json
from tests.test_stats import build_fixed_result

SAMPLE_FACTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_factory.json"


class TestSplitUnits(unittest.TestCase):
    """Section 7.4 scenario 2 and input validation for split_units."""

    def test_scenario_2_exact_values(self) -> None:
        self.assertEqual(split_units(577, 2), [289, 288])
        self.assertEqual(split_units(5, 3), [2, 2, 1])
        self.assertEqual(split_units(576, 2), [288, 288])

    def test_zero_and_single_part(self) -> None:
        self.assertEqual(split_units(0, 3), [0, 0, 0])
        self.assertEqual(split_units(816, 1), [816])

    def test_preserves_total(self) -> None:
        for total in (1, 7, 15, 233, 1280):
            for parts in (1, 2, 3):
                with self.subTest(total=total, parts=parts):
                    splits = split_units(total, parts)
                    self.assertEqual(len(splits), parts)
                    self.assertEqual(sum(splits), total)

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(TypeError):
            split_units(10.5, 2)
        with self.assertRaises(TypeError):
            split_units(True, 2)
        with self.assertRaises(TypeError):
            split_units(10, "2")
        with self.assertRaises(ValueError):
            split_units(-1, 2)
        with self.assertRaises(ValueError):
            split_units(10, 0)


class TestNpzExport(unittest.TestCase):
    """Section 7.4 scenario 11 and Section 7.5 corrupt/incomplete .npz tests."""

    def test_roundtrip_fixed_result(self) -> None:
        result = build_fixed_result()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sim.npz")
            save_simulation_npz(path, result)
            loaded = load_simulation_npz(path)
            self.assertTrue(result.equals(loaded))
            self.assertEqual(result.config.to_dict(), loaded.config.to_dict())

    def test_roundtrip_golden_30_days(self) -> None:
        factory = load_factory_json(str(SAMPLE_FACTORY_PATH))
        config = SimulationConfig.from_factory(factory, days=30, seed=42)
        result = simulate(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "golden.npz")
            save_simulation_npz(path, result)
            loaded = load_simulation_npz(path)
            self.assertTrue(result.equals(loaded))
            self.assertEqual(result.config.to_dict(), loaded.config.to_dict())

    def test_missing_file_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                load_simulation_npz(os.path.join(tmpdir, "nonexistent.npz"))

    def test_corrupt_file_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "corrupt.npz")
            with open(path, "wb") as fh:
                fh.write(b"not a valid zip or npz archive")
            with self.assertRaises(ValueError):
                load_simulation_npz(path)

    def test_incomplete_archive_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "incomplete.npz")
            np.savez(path, theoretical_capacity=np.array([960.0]))
            with self.assertRaises(ValueError):
                load_simulation_npz(path)

    def test_invalid_arguments(self) -> None:
        result = build_fixed_result()
        with self.assertRaises(TypeError):
            save_simulation_npz(123, result)
        with self.assertRaises(ValueError):
            save_simulation_npz("   ", result)
        with self.assertRaises(TypeError):
            save_simulation_npz("out.npz", {"not": "a result"})


class TestCsvExport(unittest.TestCase):
    """Section 7.4 scenario 12: long-format CSV export."""

    def test_fixed_result_csv_content_and_order(self) -> None:
        result = build_fixed_result()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "fixed.csv")
            save_simulation_csv(path, result)
            with open(path, encoding="utf-8", newline="") as fh:
                rows = list(csv.reader(fh))

        self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
        self.assertEqual(len(rows), 1 + 6)  # header + 2 machines * 3 days
        # Sorted by day first, then machine (M1, M2 for day 1, then day 2, day 3)
        self.assertEqual(rows[1][:2], ["2026-10-01", "M1"])
        self.assertEqual(rows[2][:2], ["2026-10-01", "M2"])
        self.assertEqual(rows[3][:2], ["2026-10-02", "M1"])
        self.assertEqual(rows[4][:2], ["2026-10-02", "M2"])
        self.assertEqual(rows[5][:2], ["2026-10-03", "M1"])
        self.assertEqual(rows[6][:2], ["2026-10-03", "M2"])
        self.assertEqual(int(rows[1][4]), 816)
        self.assertEqual(int(rows[3][5]), 691)
        self.assertAlmostEqual(float(rows[2][6]), 0.5)

    def test_golden_30_days_has_120_rows_and_full_precision(self) -> None:
        factory = load_factory_json(str(SAMPLE_FACTORY_PATH))
        result = simulate(SimulationConfig.from_factory(factory, days=30, seed=42))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sim.csv")
            save_simulation_csv(path, result)
            with open(path, encoding="utf-8", newline="") as fh:
                rows = list(csv.reader(fh))

        self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
        self.assertEqual(len(rows), 121)  # 1 header + 120 data rows (4 * 30)
        # Verify unrounded full precision matches matrix values
        first_eff = float(rows[1][2])
        self.assertEqual(first_eff, float(result.efficiency_pct[0, 0]))


if __name__ == "__main__":
    unittest.main()
