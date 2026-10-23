"""
product.py – Product domain entity for the factory model.

A Product represents a manufactured item with a unique code, a processing
time (seconds per unit), and a priority level (1 = highest, 5 = lowest).

Author: Kişi A
Mini Project: 02 – Factory Object Model
"""
from __future__ import annotations

from factory_model.base import FactoryEntity, validate_non_empty_str, validate_number


class Product(FactoryEntity):
    """A product that can be manufactured on one or more production lines.

    Attributes:
        product_code: Unique identifier (e.g. ``'P-A'``).
        name: Human-readable display name.
        processing_time_sec: Seconds required to produce one unit (> 0).
        priority: Integer priority 1–5 where 1 is the highest.  Defaults
            to 3.
    """

    # Required keys expected by ``from_dict``.
    _REQUIRED_FIELDS: tuple[str, ...] = (
        "product_code",
        "name",
        "processing_time_sec",
        "priority",
    )

    def __init__(
        self,
        product_code: str,
        name: str,
        processing_time_sec: float,
        priority: int = 3,
    ) -> None:
        """Create a new Product.

        Args:
            product_code: Unique product identifier (non-empty string).
            name: Display name (non-empty string).
            processing_time_sec: Processing time in seconds per unit (> 0).
            priority: Priority level 1–5 (integer only, default 3).

        Raises:
            TypeError: If any argument has the wrong type.
            ValueError: If any argument is out of its valid range.
        """
        super().__init__(name)

        self.product_code: str = validate_non_empty_str(
            product_code, "product_code"
        )

        self.processing_time_sec: float = validate_number(
            processing_time_sec,
            "processing_time_sec",
            lower=0,
            lower_inclusive=False,  # strictly > 0
        )

        # priority must be a plain int (not bool, not float)
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise TypeError("priority tam sayı (int) olmalıdır.")
        if not (1 <= priority <= 5):
            raise ValueError("priority 1 ile 5 arasında olmalıdır.")
        self.priority: int = priority

    # -- Serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a plain dictionary with keys matching the data contract.

        Keys: ``product_code``, ``name``, ``processing_time_sec``,
        ``priority``.
        """
        return {
            "product_code": self.product_code,
            "name": self.name,
            "processing_time_sec": self.processing_time_sec,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Product:
        """Reconstruct a Product from a dictionary.

        Args:
            data: Dictionary with the keys listed in ``_REQUIRED_FIELDS``.

        Returns:
            A new ``Product`` instance.

        Raises:
            ValueError: If a required key is missing from *data*.
        """
        for field in cls._REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")

        return cls(
            product_code=data["product_code"],
            name=data["name"],
            processing_time_sec=data["processing_time_sec"],
            priority=data["priority"],
        )

    # -- Representation -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Product(product_code={self.product_code!r}, "
            f"name={self.name!r}, "
            f"processing_time_sec={self.processing_time_sec}, "
            f"priority={self.priority})"
        )
