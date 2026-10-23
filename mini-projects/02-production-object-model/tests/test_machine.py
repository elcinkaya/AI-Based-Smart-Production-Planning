"""
test_machine.py – Unit tests for MachineStatus and Machine.

Covers all scenarios from Section 7.2 of the project plan, all invalid-input
cases from Section 7.4, and comprehensive state-transition tests from
Section 3.5.

Author: Kişi B
Mini Project: 02 – Production Object Model
"""

from __future__ import annotations

import os
import sys
import unittest

# Add project root to path so factory_model package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factory_model.machine import Machine, MachineStatus


# ====================================================================== #
# Helper: sample machines from Section 7.1
# ====================================================================== #

def _make_m1() -> Machine:
    """M1: CNC Lathe 1 – RUNNING, 8h, 30s, 85%, interval 200, hours 50, L1."""
    return Machine(
        machine_id="M1", name="CNC Lathe 1",
        working_hours=8, cycle_time_sec=30, efficiency_pct=85,
        maintenance_interval_hours=200,
        status=MachineStatus.RUNNING,
        operating_hours_since_maintenance=50,
        line_id="L1",
    )


def _make_m2() -> Machine:
    """M2: CNC Lathe 2 – IDLE, 16h, 45s, 90%, interval 200, hours 205, L1."""
    return Machine(
        machine_id="M2", name="CNC Lathe 2",
        working_hours=16, cycle_time_sec=45, efficiency_pct=90,
        maintenance_interval_hours=200,
        status=MachineStatus.IDLE,
        operating_hours_since_maintenance=205,
        line_id="L1",
    )


def _make_m3() -> Machine:
    """M3: Milling Machine 1 – RUNNING, 8h, 60s, 70%, interval 300, hours 100, L2."""
    return Machine(
        machine_id="M3", name="Milling Machine 1",
        working_hours=8, cycle_time_sec=60, efficiency_pct=70,
        maintenance_interval_hours=300,
        status=MachineStatus.RUNNING,
        operating_hours_since_maintenance=100,
        line_id="L2",
    )


def _make_m4() -> Machine:
    """M4: Milling Machine 2 – BROKEN, 10h, 20s, 95%, interval 250, hours 10, L2."""
    return Machine(
        machine_id="M4", name="Milling Machine 2",
        working_hours=10, cycle_time_sec=20, efficiency_pct=95,
        maintenance_interval_hours=250,
        status=MachineStatus.BROKEN,
        operating_hours_since_maintenance=10,
        line_id="L2",
    )


def _make_m5() -> Machine:
    """M5: Assembly Station – IDLE, 8h, 30s, 80%, interval 150, hours 20, L3."""
    return Machine(
        machine_id="M5", name="Assembly Station",
        working_hours=8, cycle_time_sec=30, efficiency_pct=80,
        maintenance_interval_hours=150,
        status=MachineStatus.IDLE,
        operating_hours_since_maintenance=20,
        line_id="L3",
    )


# ====================================================================== #
# 1. MachineStatus Enum tests
# ====================================================================== #

class TestMachineStatusEnum(unittest.TestCase):
    """Tests for the MachineStatus enum values."""

    def test_enum_values(self):
        """Each enum member has the correct string value."""
        self.assertEqual(MachineStatus.IDLE.value, "idle")
        self.assertEqual(MachineStatus.RUNNING.value, "running")
        self.assertEqual(MachineStatus.MAINTENANCE.value, "maintenance")
        self.assertEqual(MachineStatus.BROKEN.value, "broken")

    def test_enum_from_string(self):
        """MachineStatus can be created from a valid string value."""
        self.assertEqual(MachineStatus("idle"), MachineStatus.IDLE)
        self.assertEqual(MachineStatus("running"), MachineStatus.RUNNING)
        self.assertEqual(MachineStatus("maintenance"), MachineStatus.MAINTENANCE)
        self.assertEqual(MachineStatus("broken"), MachineStatus.BROKEN)

    def test_enum_invalid_string(self):
        """Invalid string raises ValueError."""
        with self.assertRaises(ValueError):
            MachineStatus("flying")

    def test_enum_member_count(self):
        """Exactly 4 states are defined."""
        self.assertEqual(len(MachineStatus), 4)


# ====================================================================== #
# 2. Machine creation and validation tests
# ====================================================================== #

class TestMachineCreation(unittest.TestCase):
    """Tests for valid and invalid Machine construction."""

    def test_valid_creation_defaults(self):
        """Machine with default status and operating hours."""
        m = Machine(
            machine_id="M99", name="Test Machine",
            working_hours=8, cycle_time_sec=30,
            efficiency_pct=85, maintenance_interval_hours=200,
        )
        self.assertEqual(m.machine_id, "M99")
        self.assertEqual(m.name, "Test Machine")
        self.assertEqual(m.working_hours, 8.0)
        self.assertEqual(m.cycle_time_sec, 30.0)
        self.assertEqual(m.efficiency_pct, 85.0)
        self.assertEqual(m.maintenance_interval_hours, 200.0)
        self.assertEqual(m.status, MachineStatus.IDLE)
        self.assertEqual(m.operating_hours_since_maintenance, 0.0)
        self.assertIsNone(m.line_id)

    def test_valid_creation_all_params(self):
        """Machine with all parameters explicitly set."""
        m = _make_m1()
        self.assertEqual(m.machine_id, "M1")
        self.assertEqual(m.name, "CNC Lathe 1")
        self.assertEqual(m.status, MachineStatus.RUNNING)
        self.assertEqual(m.operating_hours_since_maintenance, 50.0)
        self.assertEqual(m.line_id, "L1")

    def test_valid_boundary_working_hours_24(self):
        """24 hours is a valid upper boundary."""
        m = Machine(
            machine_id="M99", name="T", working_hours=24,
            cycle_time_sec=30, efficiency_pct=85,
            maintenance_interval_hours=200,
        )
        self.assertEqual(m.working_hours, 24.0)

    def test_valid_boundary_efficiency_100(self):
        """100% efficiency is a valid upper boundary."""
        m = Machine(
            machine_id="M99", name="T", working_hours=8,
            cycle_time_sec=30, efficiency_pct=100,
            maintenance_interval_hours=200,
        )
        self.assertEqual(m.efficiency_pct, 100.0)

    def test_repr_is_readable(self):
        """__repr__ produces a readable developer string."""
        m = _make_m1()
        r = repr(m)
        self.assertIn("M1", r)
        self.assertIn("CNC Lathe 1", r)
        self.assertIn("running", r)


# ====================================================================== #
# 3. Status transition tests (Section 3.5)
# ====================================================================== #

class TestMachineStatusTransitions(unittest.TestCase):
    """Tests for set_status() transition rules per Section 3.5."""

    # --- Valid transitions ---

    def test_idle_to_running(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.IDLE)
        m.set_status(MachineStatus.RUNNING)
        self.assertEqual(m.status, MachineStatus.RUNNING)

    def test_idle_to_maintenance(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.IDLE)
        m.set_status(MachineStatus.MAINTENANCE)
        self.assertEqual(m.status, MachineStatus.MAINTENANCE)

    def test_idle_to_broken(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.IDLE)
        m.set_status(MachineStatus.BROKEN)
        self.assertEqual(m.status, MachineStatus.BROKEN)

    def test_running_to_idle(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.RUNNING)
        m.set_status(MachineStatus.IDLE)
        self.assertEqual(m.status, MachineStatus.IDLE)

    def test_running_to_maintenance(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.RUNNING)
        m.set_status(MachineStatus.MAINTENANCE)
        self.assertEqual(m.status, MachineStatus.MAINTENANCE)

    def test_running_to_broken(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.RUNNING)
        m.set_status(MachineStatus.BROKEN)
        self.assertEqual(m.status, MachineStatus.BROKEN)

    def test_maintenance_to_idle(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        m.set_status(MachineStatus.IDLE)
        self.assertEqual(m.status, MachineStatus.IDLE)

    def test_broken_to_maintenance(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        m.set_status(MachineStatus.MAINTENANCE)
        self.assertEqual(m.status, MachineStatus.MAINTENANCE)

    # --- Same-state transitions (no-op, not an error) ---

    def test_same_state_idle(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.IDLE)
        m.set_status(MachineStatus.IDLE)  # no error
        self.assertEqual(m.status, MachineStatus.IDLE)

    def test_same_state_running(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.RUNNING)
        m.set_status(MachineStatus.RUNNING)
        self.assertEqual(m.status, MachineStatus.RUNNING)

    def test_same_state_maintenance(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        m.set_status(MachineStatus.MAINTENANCE)
        self.assertEqual(m.status, MachineStatus.MAINTENANCE)

    def test_same_state_broken(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        m.set_status(MachineStatus.BROKEN)
        self.assertEqual(m.status, MachineStatus.BROKEN)

    # --- Invalid transitions ---

    def test_maintenance_to_running_invalid(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        with self.assertRaises(ValueError):
            m.set_status(MachineStatus.RUNNING)

    def test_maintenance_to_broken_invalid(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        with self.assertRaises(ValueError):
            m.set_status(MachineStatus.BROKEN)

    def test_broken_to_idle_invalid(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        with self.assertRaises(ValueError):
            m.set_status(MachineStatus.IDLE)

    def test_broken_to_running_invalid(self):
        """Scenario 8: BROKEN → RUNNING is not allowed."""
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        with self.assertRaises(ValueError):
            m.set_status(MachineStatus.RUNNING)

    def test_set_status_non_enum_raises_type_error(self):
        m = Machine("M", "T", 8, 30, 85, 200)
        with self.assertRaises(TypeError):
            m.set_status("running")  # type: ignore


# ====================================================================== #
# 4. Availability tests
# ====================================================================== #

class TestMachineAvailability(unittest.TestCase):
    """Tests for is_available() method."""

    def test_idle_is_available(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.IDLE)
        self.assertTrue(m.is_available())

    def test_running_is_available(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.RUNNING)
        self.assertTrue(m.is_available())

    def test_maintenance_not_available(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        self.assertFalse(m.is_available())

    def test_broken_not_available(self):
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.BROKEN)
        self.assertFalse(m.is_available())


# ====================================================================== #
# 5. Capacity calculation tests
# ====================================================================== #

class TestMachineCapacity(unittest.TestCase):
    """Tests for get_theoretical_capacity and get_effective_capacity."""

    def test_m1_theoretical(self):
        """Scenario 1: M1 theoretical capacity → 960."""
        m = _make_m1()
        self.assertAlmostEqual(m.get_theoretical_capacity(), 960.0, places=2)

    def test_m1_effective(self):
        """Scenario 1: M1 effective capacity → 816."""
        m = _make_m1()
        self.assertAlmostEqual(m.get_effective_capacity(), 816.0, places=2)

    def test_m2_theoretical(self):
        """Scenario 2: M2 theoretical capacity → 1280."""
        m = _make_m2()
        self.assertAlmostEqual(m.get_theoretical_capacity(), 1280.0, places=2)

    def test_m2_effective(self):
        """Scenario 2: M2 (IDLE, available) effective capacity → 1152."""
        m = _make_m2()
        self.assertAlmostEqual(m.get_effective_capacity(), 1152.0, places=2)

    def test_m4_broken_theoretical(self):
        """Scenario 3: M4 (BROKEN) theoretical → 1800 (status-independent)."""
        m = _make_m4()
        self.assertAlmostEqual(m.get_theoretical_capacity(), 1800.0, places=2)

    def test_m4_broken_effective_zero(self):
        """Scenario 3: M4 (BROKEN) effective → 0.0."""
        m = _make_m4()
        self.assertEqual(m.get_effective_capacity(), 0.0)

    def test_m4_broken_not_available(self):
        """Scenario 3: M4 (BROKEN) is_available() → False."""
        m = _make_m4()
        self.assertFalse(m.is_available())

    def test_m1_custom_cycle_time_theoretical(self):
        """Scenario 9: M1 with cycle_time_sec=45 → theoretical 640."""
        m = _make_m1()
        self.assertAlmostEqual(
            m.get_theoretical_capacity(cycle_time_sec=45), 640.0, places=2,
        )

    def test_m1_custom_cycle_time_effective(self):
        """Scenario 9: M1 with cycle_time_sec=45 → effective 544."""
        m = _make_m1()
        self.assertAlmostEqual(
            m.get_effective_capacity(cycle_time_sec=45), 544.0, places=2,
        )

    def test_maintenance_state_effective_zero(self):
        """Machine in MAINTENANCE returns 0.0 effective capacity."""
        m = Machine("M", "T", 8, 30, 85, 200, status=MachineStatus.MAINTENANCE)
        self.assertEqual(m.get_effective_capacity(), 0.0)

    def test_theoretical_independent_of_status(self):
        """Theoretical capacity is the same regardless of status."""
        for st in MachineStatus:
            m = Machine("M", "T", 8, 30, 85, 200, status=st)
            self.assertAlmostEqual(
                m.get_theoretical_capacity(), 960.0, places=2,
                msg=f"Theoretical should be 960 for status {st.value}",
            )


# ====================================================================== #
# 6. Maintenance tests
# ====================================================================== #

class TestMachineMaintenance(unittest.TestCase):
    """Tests for needs_maintenance, perform_maintenance, add_operating_hours."""

    def test_needs_maintenance_m1_false(self):
        """Scenario 5: M1 (50h / 200h) → False."""
        m = _make_m1()
        self.assertFalse(m.needs_maintenance())

    def test_needs_maintenance_m2_true(self):
        """Scenario 5: M2 (205h / 200h) → True."""
        m = _make_m2()
        self.assertTrue(m.needs_maintenance())

    def test_needs_maintenance_m3_false(self):
        """Scenario 5: M3 (100h / 300h) → False."""
        m = _make_m3()
        self.assertFalse(m.needs_maintenance())

    def test_add_operating_hours_scenario6(self):
        """Scenario 6: M1 + 150h → counter 200, needs_maintenance True."""
        m = _make_m1()  # RUNNING, counter=50
        m.add_operating_hours(150)
        self.assertEqual(m.operating_hours_since_maintenance, 200.0)
        self.assertTrue(m.needs_maintenance())

    def test_add_operating_hours_not_running_raises(self):
        """Scenario 7: M5 (IDLE) add_operating_hours → ValueError."""
        m = _make_m5()  # IDLE
        with self.assertRaises(ValueError):
            m.add_operating_hours(5)

    def test_add_operating_hours_zero_raises(self):
        """Adding 0 hours raises ValueError (must be > 0)."""
        m = _make_m1()  # RUNNING
        with self.assertRaises(ValueError):
            m.add_operating_hours(0)

    def test_add_operating_hours_negative_raises(self):
        """Adding negative hours raises ValueError."""
        m = _make_m1()
        with self.assertRaises(ValueError):
            m.add_operating_hours(-10)

    def test_perform_maintenance_scenario4(self):
        """Scenario 4: M4 BROKEN → MAINTENANCE → perform_maintenance()."""
        m = _make_m4()  # BROKEN, hours=10
        # Step 1: BROKEN → MAINTENANCE (allowed)
        m.set_status(MachineStatus.MAINTENANCE)
        self.assertEqual(m.status, MachineStatus.MAINTENANCE)

        # Step 2: perform_maintenance
        m.perform_maintenance()
        self.assertEqual(m.status, MachineStatus.IDLE)
        self.assertEqual(m.operating_hours_since_maintenance, 0.0)

        # Step 3: effective capacity now available
        self.assertAlmostEqual(m.get_effective_capacity(), 1710.0, places=2)

    def test_perform_maintenance_not_in_maintenance_raises(self):
        """perform_maintenance on non-MAINTENANCE machine raises ValueError."""
        for st in (MachineStatus.IDLE, MachineStatus.RUNNING, MachineStatus.BROKEN):
            m = Machine("M", "T", 8, 30, 85, 200, status=st)
            with self.assertRaises(ValueError, msg=f"Should fail for {st.value}"):
                m.perform_maintenance()


# ====================================================================== #
# 7. Serialization tests (to_dict / from_dict)
# ====================================================================== #

class TestMachineSerialization(unittest.TestCase):
    """Tests for to_dict and from_dict."""

    def test_to_dict_keys(self):
        """to_dict keys must match Section 3.4 exactly."""
        m = _make_m1()
        d = m.to_dict()
        expected_keys = {
            "machine_id", "name", "working_hours", "cycle_time_sec",
            "efficiency_pct", "maintenance_interval_hours", "status",
            "operating_hours_since_maintenance", "line_id",
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values(self):
        """to_dict values match the machine attributes."""
        m = _make_m1()
        d = m.to_dict()
        self.assertEqual(d["machine_id"], "M1")
        self.assertEqual(d["name"], "CNC Lathe 1")
        self.assertEqual(d["working_hours"], 8.0)
        self.assertEqual(d["cycle_time_sec"], 30.0)
        self.assertEqual(d["efficiency_pct"], 85.0)
        self.assertEqual(d["maintenance_interval_hours"], 200.0)
        self.assertEqual(d["status"], "running")
        self.assertEqual(d["operating_hours_since_maintenance"], 50.0)
        self.assertEqual(d["line_id"], "L1")

    def test_to_dict_status_is_string(self):
        """Status in dict is a lowercase string, not MachineStatus."""
        m = _make_m4()
        d = m.to_dict()
        self.assertIsInstance(d["status"], str)
        self.assertEqual(d["status"], "broken")

    def test_to_dict_line_id_none(self):
        """line_id is None when machine is not assigned to a line."""
        m = Machine("M", "T", 8, 30, 85, 200)
        d = m.to_dict()
        self.assertIsNone(d["line_id"])

    def test_from_dict_round_trip_m4(self):
        """Scenario 10: M4 to_dict → from_dict round-trip."""
        m4 = _make_m4()
        d = m4.to_dict()

        # Verify dict has 'broken' status
        self.assertEqual(d["status"], "broken")

        # Reconstruct from dict
        m4_copy = Machine.from_dict(d)

        # Verify equality
        self.assertEqual(m4_copy.machine_id, m4.machine_id)
        self.assertEqual(m4_copy.name, m4.name)
        self.assertEqual(m4_copy.working_hours, m4.working_hours)
        self.assertEqual(m4_copy.cycle_time_sec, m4.cycle_time_sec)
        self.assertEqual(m4_copy.efficiency_pct, m4.efficiency_pct)
        self.assertEqual(m4_copy.maintenance_interval_hours, m4.maintenance_interval_hours)
        self.assertEqual(m4_copy.status, m4.status)
        self.assertEqual(
            m4_copy.operating_hours_since_maintenance,
            m4.operating_hours_since_maintenance,
        )
        self.assertEqual(m4_copy.line_id, m4.line_id)

    def test_from_dict_round_trip_all_sample_machines(self):
        """Round-trip for all 5 sample machines."""
        factories = [_make_m1, _make_m2, _make_m3, _make_m4, _make_m5]
        for factory in factories:
            with self.subTest(machine=factory.__name__):
                original = factory()
                d = original.to_dict()
                rebuilt = Machine.from_dict(d)
                self.assertEqual(original.to_dict(), rebuilt.to_dict())

    def test_from_dict_missing_field_raises(self):
        """from_dict with missing 'machine_id' raises ValueError."""
        data = {
            "name": "T", "working_hours": 8, "cycle_time_sec": 30,
            "efficiency_pct": 85, "maintenance_interval_hours": 200,
            "status": "idle", "operating_hours_since_maintenance": 0,
            "line_id": None,
            # machine_id is missing
        }
        with self.assertRaises(ValueError) as ctx:
            Machine.from_dict(data)
        self.assertIn("machine_id", str(ctx.exception))

    def test_from_dict_invalid_status_raises(self):
        """from_dict with invalid status string 'flying' raises ValueError."""
        data = {
            "machine_id": "M1", "name": "T", "working_hours": 8,
            "cycle_time_sec": 30, "efficiency_pct": 85,
            "maintenance_interval_hours": 200, "status": "flying",
            "operating_hours_since_maintenance": 0, "line_id": None,
        }
        with self.assertRaises(ValueError) as ctx:
            Machine.from_dict(data)
        self.assertIn("flying", str(ctx.exception))


# ====================================================================== #
# 8. Invalid input tests (Section 7.4)
# ====================================================================== #

class TestMachineInvalidInputs(unittest.TestCase):
    """Invalid-input tests from Section 7.4 – all must raise ValueError."""

    def _make_valid_kwargs(self) -> dict:
        """Return a valid kwargs dict for Machine(); tests override one value."""
        return dict(
            machine_id="M1", name="T", working_hours=8,
            cycle_time_sec=30, efficiency_pct=85,
            maintenance_interval_hours=200,
        )

    def test_efficiency_pct_zero(self):
        """efficiency_pct=0 raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["efficiency_pct"] = 0
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_efficiency_pct_120(self):
        """efficiency_pct=120 raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["efficiency_pct"] = 120
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_working_hours_zero(self):
        """working_hours=0 raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["working_hours"] = 0
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_working_hours_25(self):
        """working_hours=25 raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["working_hours"] = 25
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_cycle_time_sec_zero(self):
        """cycle_time_sec=0 raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["cycle_time_sec"] = 0
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_negative_maintenance_interval(self):
        """Negative maintenance_interval_hours raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["maintenance_interval_hours"] = -100
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_empty_machine_id(self):
        """Empty machine_id raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["machine_id"] = ""
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_whitespace_machine_id(self):
        """Whitespace-only machine_id raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["machine_id"] = "   "
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_string_instead_of_number_working_hours(self):
        """working_hours='abc' raises TypeError or ValueError."""
        kw = self._make_valid_kwargs()
        kw["working_hours"] = "abc"
        with self.assertRaises((ValueError, TypeError)):
            Machine(**kw)

    def test_string_instead_of_number_cycle_time(self):
        """cycle_time_sec='abc' raises TypeError or ValueError."""
        kw = self._make_valid_kwargs()
        kw["cycle_time_sec"] = "abc"
        with self.assertRaises((ValueError, TypeError)):
            Machine(**kw)

    def test_string_instead_of_number_efficiency(self):
        """efficiency_pct='abc' raises TypeError or ValueError."""
        kw = self._make_valid_kwargs()
        kw["efficiency_pct"] = "abc"
        with self.assertRaises((ValueError, TypeError)):
            Machine(**kw)

    def test_negative_operating_hours(self):
        """Negative operating_hours_since_maintenance raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["operating_hours_since_maintenance"] = -5
        with self.assertRaises(ValueError):
            Machine(**kw)

    def test_boolean_as_number(self):
        """Boolean value for numeric field raises TypeError or ValueError."""
        kw = self._make_valid_kwargs()
        kw["working_hours"] = True
        with self.assertRaises((ValueError, TypeError)):
            Machine(**kw)

    def test_non_enum_status_in_init(self):
        """Non-MachineStatus status in __init__ raises TypeError."""
        kw = self._make_valid_kwargs()
        kw["status"] = "idle"
        with self.assertRaises(TypeError):
            Machine(**kw)

    def test_empty_name(self):
        """Empty name raises ValueError."""
        kw = self._make_valid_kwargs()
        kw["name"] = ""
        with self.assertRaises(ValueError):
            Machine(**kw)


# ====================================================================== #
# 9. Comprehensive Section 7.2 scenario tests
# ====================================================================== #

class TestMachineWordScenarios(unittest.TestCase):
    """All 10 machine scenarios from WORD Section 7.2."""

    def test_scenario_1_m1_capacity(self):
        """Scenario 1: M1 theoretical=960, effective=816."""
        m = _make_m1()
        self.assertAlmostEqual(m.get_theoretical_capacity(), 960.0, places=2)
        self.assertAlmostEqual(m.get_effective_capacity(), 816.0, places=2)

    def test_scenario_2_m2_capacity(self):
        """Scenario 2: M2 (IDLE) theoretical=1280, effective=1152."""
        m = _make_m2()
        self.assertTrue(m.is_available())
        self.assertAlmostEqual(m.get_theoretical_capacity(), 1280.0, places=2)
        self.assertAlmostEqual(m.get_effective_capacity(), 1152.0, places=2)

    def test_scenario_3_m4_broken(self):
        """Scenario 3: M4 (BROKEN) theoretical=1800, effective=0.0, not available."""
        m = _make_m4()
        self.assertAlmostEqual(m.get_theoretical_capacity(), 1800.0, places=2)
        self.assertEqual(m.get_effective_capacity(), 0.0)
        self.assertFalse(m.is_available())

    def test_scenario_4_m4_repair(self):
        """Scenario 4: M4 BROKEN→MAINTENANCE→perform_maintenance → IDLE, counter=0, eff=1710."""
        m = _make_m4()
        m.set_status(MachineStatus.MAINTENANCE)
        m.perform_maintenance()
        self.assertEqual(m.status, MachineStatus.IDLE)
        self.assertEqual(m.operating_hours_since_maintenance, 0.0)
        self.assertAlmostEqual(m.get_effective_capacity(), 1710.0, places=2)

    def test_scenario_5_needs_maintenance(self):
        """Scenario 5: M1=False, M2=True (205≥200), M3=False."""
        self.assertFalse(_make_m1().needs_maintenance())
        self.assertTrue(_make_m2().needs_maintenance())
        self.assertFalse(_make_m3().needs_maintenance())

    def test_scenario_6_add_hours(self):
        """Scenario 6: M1 + 150h → counter=200, needs_maintenance=True."""
        m = _make_m1()
        m.add_operating_hours(150)
        self.assertEqual(m.operating_hours_since_maintenance, 200.0)
        self.assertTrue(m.needs_maintenance())

    def test_scenario_7_add_hours_idle_raises(self):
        """Scenario 7: M5 (IDLE) add_operating_hours(5) → ValueError."""
        m = _make_m5()
        with self.assertRaises(ValueError):
            m.add_operating_hours(5)

    def test_scenario_8_broken_to_running_raises(self):
        """Scenario 8: M3 RUNNING→BROKEN ok; BROKEN→RUNNING → ValueError."""
        m = _make_m3()
        m.set_status(MachineStatus.BROKEN)  # RUNNING → BROKEN: allowed
        self.assertEqual(m.status, MachineStatus.BROKEN)
        with self.assertRaises(ValueError):
            m.set_status(MachineStatus.RUNNING)  # BROKEN → RUNNING: not allowed

    def test_scenario_9_custom_cycle_time(self):
        """Scenario 9: M1 with cycle_time_sec=45 → theoretical=640, effective=544."""
        m = _make_m1()
        self.assertAlmostEqual(
            m.get_theoretical_capacity(cycle_time_sec=45), 640.0, places=2,
        )
        self.assertAlmostEqual(
            m.get_effective_capacity(cycle_time_sec=45), 544.0, places=2,
        )

    def test_scenario_10_round_trip(self):
        """Scenario 10: M4 to_dict→from_dict → status='broken', equal."""
        m4 = _make_m4()
        d = m4.to_dict()
        self.assertEqual(d["status"], "broken")

        m4_copy = Machine.from_dict(d)
        self.assertEqual(m4_copy.status, MachineStatus.BROKEN)
        self.assertEqual(m4_copy.to_dict(), d)


# ====================================================================== #
# 10. Line-id setter tests (used by ProductionLine)
# ====================================================================== #

class TestMachineLineIdSetter(unittest.TestCase):
    """Tests for the line_id setter (used by ProductionLine)."""

    def test_set_line_id(self):
        m = Machine("M", "T", 8, 30, 85, 200)
        self.assertIsNone(m.line_id)
        m.line_id = "L1"
        self.assertEqual(m.line_id, "L1")

    def test_clear_line_id(self):
        m = Machine("M", "T", 8, 30, 85, 200, line_id="L1")
        m.line_id = None
        self.assertIsNone(m.line_id)

    def test_set_empty_line_id_raises(self):
        m = Machine("M", "T", 8, 30, 85, 200)
        with self.assertRaises(ValueError):
            m.line_id = ""


if __name__ == "__main__":
    unittest.main()
