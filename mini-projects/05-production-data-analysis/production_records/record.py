"""
record.py – Production record data model and validation.

This module defines:
- SHIFT_HOURS: Standard shift duration constant (8.0 hours).
- Shift: Enum representing production shifts (morning, afternoon, night).
- ProductionRecord: Domain class representing a single machine's production
  summary in one shift, implementing full validation and serialization contracts.

Author: Kişi A
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

try:
    from factory_model.base import validate_non_empty_str, validate_number
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from factory_model.base import validate_non_empty_str, validate_number


# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

SHIFT_HOURS: float = 8.0


class Shift(Enum):
    """Production shift enumeration.

    Members use uppercase names with lowercase string values for JSON/CSV
    compatibility.
    """

    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"


# ---------------------------------------------------------------------------
# ProductionRecord Entity
# ---------------------------------------------------------------------------

class ProductionRecord:
    """Represents a production summary of a machine during a single shift.

    Attributes:
        record_id: Unique record ID assigned by store (>= 1) or None.
        production_date: Calendar date of production (datetime.date).
        shift: Shift of production (Shift enum).
        machine_id: Machine identifier (non-empty str).
        product_code: Product code produced (non-empty str).
        planned_units: Planned production quantity (int > 0).
        actual_units: Actual production quantity (int >= 0).
        downtime_hours: Downtime occurred during the shift (0.0 <= x <= 8.0).
    """

    _REQUIRED_FIELDS: tuple[str, ...] = (
        "production_date",
        "shift",
        "machine_id",
        "product_code",
        "planned_units",
        "actual_units",
        "downtime_hours",
    )

    def __init__(
        self,
        production_date: datetime.date | str,
        shift: Shift | str,
        machine_id: str,
        product_code: str,
        planned_units: int,
        actual_units: int,
        downtime_hours: float = 0.0,
        record_id: int | None = None,
    ) -> None:
        """Initialize and validate a ProductionRecord instance.

        Args:
            production_date: Production date as datetime.date or ISO string (YYYY-MM-DD).
            shift: Shift as Shift enum member or lowercase string value.
            machine_id: Unique machine identifier (non-empty string).
            product_code: Unique product code (non-empty string).
            planned_units: Target output in units (integer > 0).
            actual_units: Actual output in units (integer >= 0).
            downtime_hours: Downtime in hours during the shift (0.0 <= x <= 8.0).
            record_id: Optional unique record ID (integer >= 1 or None).

        Raises:
            TypeError: If an argument has an invalid type.
            ValueError: If an argument contains an invalid value or out of bounds.
        """
        # 1. record_id validation (None or int >= 1)
        if record_id is not None:
            if isinstance(record_id, bool) or not isinstance(record_id, int):
                raise TypeError("Kayıt numarası (record_id) bir tam sayı (int) olmalıdır.")
            if record_id < 1:
                raise ValueError("Kayıt numarası (record_id) 1 veya daha büyük olmalıdır.")
        self.record_id: int | None = record_id

        # 2. production_date validation (datetime.date or valid ISO string)
        self.production_date: datetime.date = self._validate_date(production_date)

        # 3. shift validation (Shift enum or valid string)
        self.shift: Shift = self._validate_shift(shift)

        # 4. machine_id validation
        self.machine_id: str = validate_non_empty_str(machine_id, "machine_id")

        # 5. product_code validation
        self.product_code: str = validate_non_empty_str(product_code, "product_code")

        # 6. planned_units validation (strict int > 0, no bool, no float)
        if isinstance(planned_units, bool) or not isinstance(planned_units, (int, float)):
            raise TypeError("Planlanan miktar (planned_units) tam sayı (int) olmalıdır.")
        if isinstance(planned_units, float):
            raise ValueError("Planlanan miktar (planned_units) ondalıklı olamaz, tam sayı olmalıdır.")
        if planned_units <= 0:
            raise ValueError("Planlanan miktar (planned_units) sıfırdan büyük olmalıdır.")
        self.planned_units: int = planned_units

        # 7. actual_units validation (strict int >= 0, no bool, no float)
        if isinstance(actual_units, bool) or not isinstance(actual_units, (int, float)):
            raise TypeError("Gerçekleşen miktar (actual_units) tam sayı (int) olmalıdır.")
        if isinstance(actual_units, float):
            raise ValueError("Gerçekleşen miktar (actual_units) ondalıklı olamaz, tam sayı olmalıdır.")
        if actual_units < 0:
            raise ValueError("Gerçekleşen miktar (actual_units) negatif olamaz.")
        self.actual_units: int = actual_units

        # 8. downtime_hours validation (float 0.0 <= x <= 8.0, no bool)
        if isinstance(downtime_hours, bool):
            raise TypeError("Duruş süresi (downtime_hours) bool kabul edilmez.")
        num_downtime = validate_number(
            downtime_hours,
            "downtime_hours",
            lower=0.0,
            upper=SHIFT_HOURS,
            lower_inclusive=True,
            upper_inclusive=True,
        )
        self.downtime_hours: float = float(num_downtime)

    @staticmethod
    def _validate_date(date_val: Any) -> datetime.date:
        """Validate and convert date input to datetime.date."""
        if isinstance(date_val, datetime.datetime):
            return date_val.date()
        if isinstance(date_val, datetime.date):
            return date_val
        if isinstance(date_val, str):
            clean_str = date_val.strip()
            # Enforce strict ISO format YYYY-MM-DD
            parts = clean_str.split("-")
            if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
                raise ValueError(
                    f"Geçersiz tarih biçimi: '{date_val}'. Tarih 'YYYY-MM-DD' formatında olmalıdır."
                )
            try:
                return datetime.date.fromisoformat(clean_str)
            except ValueError as err:
                raise ValueError(
                    f"Geçersiz takvim tarihi: '{date_val}'. Lütfen geçerli bir tarih giriniz."
                ) from err
        raise TypeError("Üretim tarihi (production_date) datetime.date veya ISO formatında metin olmalıdır.")

    @staticmethod
    def _validate_shift(shift_val: Any) -> Shift:
        """Validate and convert shift input to Shift enum."""
        if isinstance(shift_val, Shift):
            return shift_val
        if isinstance(shift_val, str):
            clean_val = shift_val.strip().lower()
            try:
                return Shift(clean_val)
            except ValueError as err:
                valid_options = ", ".join([f"'{s.value}'" for s in Shift])
                raise ValueError(
                    f"Geçersiz vardiya: '{shift_val}'. Geçerli değerler: {valid_options}."
                ) from err
        raise TypeError("Vardiya (shift) Shift enum veya geçerli bir metin değeri olmalıdır.")

    def get_key(self) -> tuple[str, str, str]:
        """Return the uniqueness key for the record: (ISO date, shift value, machine_id).

        Returns:
            A tuple of (production_date_iso, shift_value, machine_id).
        """
        return (
            self.production_date.isoformat(),
            self.shift.value,
            self.machine_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the record into a plain dictionary matching Section 3.2 data contract.

        Returns:
            Dictionary containing record fields.
        """
        return {
            "record_id": self.record_id,
            "production_date": self.production_date.isoformat(),
            "shift": self.shift.value,
            "machine_id": self.machine_id,
            "product_code": self.product_code,
            "planned_units": self.planned_units,
            "actual_units": self.actual_units,
            "downtime_hours": self.downtime_hours,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductionRecord:
        """Reconstruct a ProductionRecord from a dictionary.

        Args:
            data: Dictionary containing record fields.

        Returns:
            A new ProductionRecord instance.

        Raises:
            TypeError: If data is not a dict.
            ValueError: If any required field is missing.
        """
        if not isinstance(data, dict):
            raise TypeError("Kayıt verisi bir sözlük (dict) olmalıdır.")

        for field in cls._REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")

        return cls(
            production_date=data["production_date"],
            shift=data["shift"],
            machine_id=data["machine_id"],
            product_code=data["product_code"],
            planned_units=data["planned_units"],
            actual_units=data["actual_units"],
            downtime_hours=data["downtime_hours"],
            record_id=data.get("record_id"),
        )

    def __repr__(self) -> str:
        """Return an informative string representation of the record."""
        return (
            f"ProductionRecord(record_id={self.record_id}, "
            f"production_date={self.production_date.isoformat()!r}, "
            f"shift={self.shift.value!r}, machine_id={self.machine_id!r}, "
            f"product_code={self.product_code!r}, planned_units={self.planned_units}, "
            f"actual_units={self.actual_units}, downtime_hours={self.downtime_hours})"
        )

    def __eq__(self, other: Any) -> bool:
        """Compare two records based on their to_dict() representations."""
        if not isinstance(other, ProductionRecord):
            return False
        return self.to_dict() == other.to_dict()
