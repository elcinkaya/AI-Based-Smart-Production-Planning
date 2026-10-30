"""
test_generate_records.py – Unit tests for deterministic synthetic records generation.

Tests:
- Same seed produces identical records.
- Different seeds produce different records.
- Exactly 150 records for 30 days on sample_factory.json.
- Broken / unavailable machines (M4) do not generate records.
- All record keys are unique (no duplicate date, shift, machine_id).
- Planned units do not exceed shift capacity.
- Downtime hours stay strictly within the [0.0, 8.0] range.

Author: Kişi A
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import unittest
from pathlib import Path

from factory_model.serialization import load_factory_json
from factory_model import calculations
from production_records.record import SHIFT_HOURS
from production_records.generate_records import generate_records


class TestGenerateRecords(unittest.TestCase):
    """Test suite for generate_records generator function."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load sample factory data."""
        base_dir = Path(__file__).resolve().parent.parent
        cls.factory_path = str(base_dir / "data" / "sample_factory.json")
        cls.factory = load_factory_json(cls.factory_path)

    def test_same_seed_identical_results(self) -> None:
        """Test that identical seeds generate exactly identical records."""
        records_a = generate_records(self.factory, "2026-10-01", 10, seed=42)
        records_b = generate_records(self.factory, "2026-10-01", 10, seed=42)

        self.assertEqual(len(records_a), len(records_b))
        for r_a, r_b in zip(records_a, records_b):
            self.assertEqual(r_a, r_b)

    def test_different_seed_different_results(self) -> None:
        """Test that different seeds generate differing records."""
        records_42 = generate_records(self.factory, "2026-10-01", 10, seed=42)
        records_99 = generate_records(self.factory, "2026-10-01", 10, seed=99)

        self.assertEqual(len(records_42), len(records_99))
        diff_count = sum(1 for a, b in zip(records_42, records_99) if a != b)
        self.assertGreater(diff_count, 0)

    def test_record_count_for_30_days(self) -> None:
        """Test that 30 days generates exactly 150 records (5 per day)."""
        records = generate_records(self.factory, "2026-10-01", 30, seed=42)
        self.assertEqual(len(records), 150)

    def test_broken_machine_excluded(self) -> None:
        """Test that broken or maintenance machines (M4) are excluded."""
        records = generate_records(self.factory, "2026-10-01", 30, seed=42)
        machines = {r.machine_id for r in records}
        self.assertNotIn("M4", machines)
        self.assertEqual(machines, {"M1", "M2", "M3", "M5"})

    def test_keys_are_unique(self) -> None:
        """Test that each (production_date, shift, machine_id) triple is unique."""
        records = generate_records(self.factory, "2026-10-01", 30, seed=42)
        keys = [r.get_key() for r in records]
        self.assertEqual(len(keys), len(set(keys)))

    def test_planned_units_within_shift_capacity(self) -> None:
        """Test that planned_units does not exceed shift capacity for any machine."""
        records = generate_records(self.factory, "2026-10-01", 30, seed=42)

        # Precompute max shift capacity for each available machine
        capacity_map: dict[str, float] = {}
        for m in self.factory["machines"]:
            if m.is_available():
                shifts = max(1, round(m.working_hours / SHIFT_HOURS))
                theo = calculations.theoretical_capacity(m.working_hours, m.cycle_time_sec)
                eff = calculations.effective_capacity(theo, m.efficiency_pct)
                capacity_map[m.machine_id] = eff / shifts

        for r in records:
            max_cap = capacity_map[r.machine_id]
            # Since factor is uniform(0.80, 1.00), planned_units should be <= round(max_cap)
            self.assertLessEqual(
                r.planned_units,
                round(max_cap),
                f"Planned units {r.planned_units} exceeds capacity {max_cap} for machine {r.machine_id}",
            )
            self.assertGreater(r.planned_units, 0)

    def test_downtime_hours_within_bounds(self) -> None:
        """Test that downtime_hours is always between 0.0 and 8.0."""
        records = generate_records(self.factory, "2026-10-01", 30, seed=42)
        for r in records:
            self.assertGreaterEqual(r.downtime_hours, 0.0)
            self.assertLessEqual(r.downtime_hours, SHIFT_HOURS)

    def test_invalid_arguments(self) -> None:
        """Test argument validation in generate_records."""
        with self.assertRaises((ValueError, TypeError)):
            generate_records("not-a-dict", "2026-10-01", 10)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            generate_records(self.factory, "2026-10-01", 0)
        with self.assertRaises(ValueError):
            generate_records(self.factory, "2026-10-01", -5)
        with self.assertRaises(ValueError):
            generate_records(self.factory, "invalid-date", 10)


if __name__ == "__main__":
    unittest.main()
