"""
machine.py – Machine and MachineStatus for the factory object model.

This module defines:
- MachineStatus: Enum for machine states (IDLE, RUNNING, MAINTENANCE, BROKEN).
- Machine: FactoryEntity subclass representing a production machine with
  capacity calculation, status management, and maintenance tracking.

Capacity calculations delegate to Mini Project 1's calculations module;
no formulas are reimplemented here.

Author: Kişi B
Mini Project: 02 – Production Object Model
"""

from __future__ import annotations

from enum import Enum

from factory_model.base import FactoryEntity, validate_non_empty_str, validate_number
from factory_model import calculations


class MachineStatus(Enum):
    """Enum representing possible machine operational states.

    Values are lowercase strings suitable for JSON serialization.
    Transition rules are enforced by ``Machine.set_status()``.
    """

    IDLE = "idle"
    RUNNING = "running"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"


# Allowed state transitions per Section 3.5 of the project plan.
_ALLOWED_TRANSITIONS: dict[MachineStatus, set[MachineStatus]] = {
    MachineStatus.IDLE: {
        MachineStatus.RUNNING,
        MachineStatus.MAINTENANCE,
        MachineStatus.BROKEN,
    },
    MachineStatus.RUNNING: {
        MachineStatus.IDLE,
        MachineStatus.MAINTENANCE,
        MachineStatus.BROKEN,
    },
    MachineStatus.MAINTENANCE: {MachineStatus.IDLE},
    MachineStatus.BROKEN: {MachineStatus.MAINTENANCE},
}


class Machine(FactoryEntity):
    """A production machine with capacity, status, and maintenance tracking.

    Uses Mini Project 1's calculations module for capacity computations.
    State transitions follow the rules defined in Section 3.5.

    Attributes:
        machine_id: Unique machine identifier (e.g. 'M1').
        working_hours: Daily working time in hours/day (0 < x <= 24).
        cycle_time_sec: Default cycle time in seconds/unit (x > 0).
        efficiency_pct: Machine efficiency as percentage (0 < x <= 100).
        maintenance_interval_hours: Hours between required maintenance (x > 0).
        status: Current machine state (MachineStatus).
        operating_hours_since_maintenance: Hours since last maintenance (x >= 0).
        line_id: Production line ID or None if unassigned.
    """

    def __init__(
        self,
        machine_id: str,
        name: str,
        working_hours: float,
        cycle_time_sec: float,
        efficiency_pct: float,
        maintenance_interval_hours: float,
        status: MachineStatus = MachineStatus.IDLE,
        operating_hours_since_maintenance: float = 0.0,
        line_id: str | None = None,
    ) -> None:
        """Initialize a Machine with validated parameters.

        Args:
            machine_id: Unique identifier, non-empty string.
            name: Machine name, non-empty string.
            working_hours: Daily working time (hours/day), 0 < x <= 24.
            cycle_time_sec: Cycle time (seconds/unit), x > 0.
            efficiency_pct: Efficiency percentage, 0 < x <= 100.
            maintenance_interval_hours: Maintenance interval (hours), x > 0.
            status: Initial machine state, defaults to IDLE.
            operating_hours_since_maintenance: Hours since maintenance, x >= 0.
            line_id: Production line ID or None.

        Raises:
            ValueError: If any numeric value is out of range or string is empty.
            TypeError: If status is not a MachineStatus instance.
        """
        super().__init__(name)

        self._machine_id = validate_non_empty_str(machine_id, "machine_id")

        self._working_hours = validate_number(
            working_hours, "working_hours",
            lower=0, upper=24, lower_inclusive=False, upper_inclusive=True,
        )
        self._cycle_time_sec = validate_number(
            cycle_time_sec, "cycle_time_sec",
            lower=0, lower_inclusive=False,
        )
        self._efficiency_pct = validate_number(
            efficiency_pct, "efficiency_pct",
            lower=0, upper=100, lower_inclusive=False, upper_inclusive=True,
        )
        self._maintenance_interval_hours = validate_number(
            maintenance_interval_hours, "maintenance_interval_hours",
            lower=0, lower_inclusive=False,
        )

        if not isinstance(status, MachineStatus):
            raise TypeError("Makine durumu MachineStatus enum değeri olmalıdır.")
        self._status = status

        self._operating_hours_since_maintenance = validate_number(
            operating_hours_since_maintenance, "operating_hours_since_maintenance",
            lower=0, lower_inclusive=True,
        )

        if line_id is not None:
            validate_non_empty_str(line_id, "line_id")
        self._line_id = line_id

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #

    @property
    def machine_id(self) -> str:
        """Unique machine identifier."""
        return self._machine_id

    @property
    def working_hours(self) -> float:
        """Daily working time in hours/day."""
        return self._working_hours

    @property
    def cycle_time_sec(self) -> float:
        """Default cycle time in seconds/unit."""
        return self._cycle_time_sec

    @property
    def efficiency_pct(self) -> float:
        """Machine efficiency as a percentage."""
        return self._efficiency_pct

    @property
    def maintenance_interval_hours(self) -> float:
        """Hours between required maintenance sessions."""
        return self._maintenance_interval_hours

    @property
    def status(self) -> MachineStatus:
        """Current machine operational state."""
        return self._status

    @property
    def operating_hours_since_maintenance(self) -> float:
        """Hours of operation since last maintenance."""
        return self._operating_hours_since_maintenance

    @property
    def line_id(self) -> str | None:
        """ID of the production line this machine belongs to."""
        return self._line_id

    @line_id.setter
    def line_id(self, value: str | None) -> None:
        """Set line_id (used by ProductionLine when adding/removing machines)."""
        if value is not None:
            validate_non_empty_str(value, "line_id")
        self._line_id = value

    # ------------------------------------------------------------------ #
    # Status management (Section 3.5)
    # ------------------------------------------------------------------ #

    def set_status(self, new_status: MachineStatus) -> None:
        """Change machine status following the allowed transition rules.

        A same-state transition is silently ignored (no-op, not an error).

        Args:
            new_status: The target MachineStatus.

        Raises:
            TypeError: If *new_status* is not a MachineStatus.
            ValueError: If the transition is not allowed.
        """
        if not isinstance(new_status, MachineStatus):
            raise TypeError("Makine durumu MachineStatus enum değeri olmalıdır.")

        if new_status == self._status:
            return  # Same-state transition: no-op

        allowed = _ALLOWED_TRANSITIONS[self._status]
        if new_status not in allowed:
            raise ValueError(
                f"'{self._status.value}' durumundan '{new_status.value}' "
                f"durumuna geçiş izin verilmiyor."
            )

        self._status = new_status

    def is_available(self) -> bool:
        """Check whether the machine is available for production.

        Returns:
            True if status is IDLE or RUNNING.
        """
        return self._status in (MachineStatus.IDLE, MachineStatus.RUNNING)

    # ------------------------------------------------------------------ #
    # Capacity calculations (delegates to MP1 calculations module)
    # ------------------------------------------------------------------ #

    def get_theoretical_capacity(
        self, cycle_time_sec: float | None = None,
    ) -> float:
        """Calculate theoretical daily capacity in units/day.

        Independent of machine status.  Delegates to
        ``calculations.theoretical_capacity`` from Mini Project 1.

        Args:
            cycle_time_sec: Override cycle time for product-specific
                calculation.  Uses the machine's own value when None.

        Returns:
            Theoretical capacity in units/day.
        """
        ct = cycle_time_sec if cycle_time_sec is not None else self._cycle_time_sec
        return calculations.theoretical_capacity(self._working_hours, ct)

    def get_effective_capacity(
        self, cycle_time_sec: float | None = None,
    ) -> float:
        """Calculate effective daily capacity in units/day.

        Returns 0.0 when the machine is unavailable (MAINTENANCE or BROKEN).
        Delegates to ``calculations.effective_capacity`` from Mini Project 1.

        Args:
            cycle_time_sec: Override cycle time for product-specific
                calculation.  Uses the machine's own value when None.

        Returns:
            Effective capacity in units/day, or 0.0 if unavailable.
        """
        if not self.is_available():
            return 0.0

        theo = self.get_theoretical_capacity(cycle_time_sec)
        return calculations.effective_capacity(theo, self._efficiency_pct)

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #

    def needs_maintenance(self) -> bool:
        """Check whether the machine needs maintenance.

        Returns:
            True if operating_hours_since_maintenance >=
            maintenance_interval_hours.
        """
        return (
            self._operating_hours_since_maintenance
            >= self._maintenance_interval_hours
        )

    def add_operating_hours(self, hours: float) -> None:
        """Add operating hours to the maintenance counter.

        Only allowed while the machine status is RUNNING.

        Args:
            hours: Number of hours to add (must be > 0).

        Raises:
            ValueError: If machine is not RUNNING or *hours* is not > 0.
        """
        if self._status != MachineStatus.RUNNING:
            raise ValueError(
                "Çalışma saati yalnızca RUNNING durumundaki makineye eklenebilir."
            )
        hours = validate_number(hours, "hours", lower=0, lower_inclusive=False)
        self._operating_hours_since_maintenance += hours

    def perform_maintenance(self) -> None:
        """Perform maintenance: reset the hour counter, set status to IDLE.

        Only allowed in MAINTENANCE state.

        Raises:
            ValueError: If machine is not in MAINTENANCE state.
        """
        if self._status != MachineStatus.MAINTENANCE:
            raise ValueError(
                "Bakım yalnızca MAINTENANCE durumundaki makinede yapılabilir."
            )
        self._operating_hours_since_maintenance = 0.0
        self._status = MachineStatus.IDLE

    # ------------------------------------------------------------------ #
    # Serialization (Section 3.4 data contract)
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Convert machine to a dictionary matching the Section 3.4 contract.

        Returns:
            Dictionary with keys: machine_id, name, working_hours,
            cycle_time_sec, efficiency_pct, maintenance_interval_hours,
            status (as string value), operating_hours_since_maintenance,
            line_id.
        """
        return {
            "machine_id": self._machine_id,
            "name": self.name,
            "working_hours": self._working_hours,
            "cycle_time_sec": self._cycle_time_sec,
            "efficiency_pct": self._efficiency_pct,
            "maintenance_interval_hours": self._maintenance_interval_hours,
            "status": self._status.value,
            "operating_hours_since_maintenance": self._operating_hours_since_maintenance,
            "line_id": self._line_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Machine:
        """Create a Machine instance from a dictionary.

        Args:
            data: Dictionary with all required keys from Section 3.4.

        Returns:
            A new Machine instance.

        Raises:
            ValueError: If a required key is missing or status text is invalid.
        """
        required_fields = [
            "machine_id", "name", "working_hours", "cycle_time_sec",
            "efficiency_pct", "maintenance_interval_hours", "status",
            "operating_hours_since_maintenance", "line_id",
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")

        # Convert status string to MachineStatus enum
        status_str = data["status"]
        try:
            status = MachineStatus(status_str)
        except ValueError:
            raise ValueError(f"Geçersiz makine durumu: '{status_str}'")

        return cls(
            machine_id=data["machine_id"],
            name=data["name"],
            working_hours=data["working_hours"],
            cycle_time_sec=data["cycle_time_sec"],
            efficiency_pct=data["efficiency_pct"],
            maintenance_interval_hours=data["maintenance_interval_hours"],
            status=status,
            operating_hours_since_maintenance=data["operating_hours_since_maintenance"],
            line_id=data["line_id"],
        )

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Machine(machine_id={self._machine_id!r}, name={self.name!r}, "
            f"status={self._status.value!r}, line_id={self._line_id!r})"
        )
