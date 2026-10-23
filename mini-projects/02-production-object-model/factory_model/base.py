"""
base.py – Base class and shared validation helpers for the factory model.

Provides the FactoryEntity abstract base class that all domain entities
(Product, Machine, ProductionLine) inherit from.  Also exposes two
reusable validation functions used across the entire model layer.

Author: Kişi A
Mini Project: 02 – Factory Object Model
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_non_empty_str(value, field_name: str) -> str:
    """Validate that *value* is a non-empty string.

    Args:
        value: The value to validate.
        field_name: Human-readable field name used in the error message.

    Returns:
        The stripped string.

    Raises:
        TypeError: If *value* is not a ``str``.
        ValueError: If *value* is empty or whitespace-only.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name} bir metin (str) olmalıdır.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} boş olamaz.")
    return stripped


def validate_number(
    value,
    field_name: str,
    lower: float | None = None,
    upper: float | None = None,
    lower_inclusive: bool = True,
    upper_inclusive: bool = True,
) -> float:
    """Validate that *value* is numeric and within the given bounds.

    Args:
        value: The value to validate.
        field_name: Human-readable field name used in the error message.
        lower: Optional lower bound.
        upper: Optional upper bound.
        lower_inclusive: Whether the lower bound is inclusive (>=) or
            exclusive (>).  Defaults to ``True``.
        upper_inclusive: Whether the upper bound is inclusive (<=) or
            exclusive (<).  Defaults to ``True``.

    Returns:
        The value cast to ``float``.

    Raises:
        TypeError: If *value* is not numeric (``int`` or ``float``).
            ``bool`` is explicitly rejected.
        ValueError: If *value* is outside the specified bounds.
    """
    # Reject booleans explicitly (bool is a subclass of int in Python)
    if isinstance(value, bool):
        raise TypeError(f"{field_name} sayısal bir değer olmalıdır (bool kabul edilmez).")
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} sayısal bir değer olmalıdır.")

    num = float(value)

    # Lower bound check
    if lower is not None:
        if lower_inclusive and num < lower:
            raise ValueError(
                f"{field_name} {lower} veya daha büyük olmalıdır."
            )
        if not lower_inclusive and num <= lower:
            raise ValueError(
                f"{field_name} {lower} değerinden büyük olmalıdır."
            )

    # Upper bound check
    if upper is not None:
        if upper_inclusive and num > upper:
            raise ValueError(
                f"{field_name} {upper} veya daha küçük olmalıdır."
            )
        if not upper_inclusive and num >= upper:
            raise ValueError(
                f"{field_name} {upper} değerinden küçük olmalıdır."
            )

    return num


# ---------------------------------------------------------------------------
# Base entity class
# ---------------------------------------------------------------------------

class FactoryEntity:
    """Abstract base for all factory domain objects.

    Every entity has a ``name`` attribute validated on construction.
    Subclasses must override ``to_dict`` and ``from_dict``; the base
    implementations raise ``NotImplementedError``.
    """

    def __init__(self, name: str) -> None:
        """Initialize the entity with a validated *name*.

        Args:
            name: Display name of the entity (must be non-empty).

        Raises:
            TypeError: If *name* is not a string.
            ValueError: If *name* is empty or whitespace-only.
        """
        self.name: str = validate_non_empty_str(name, "name")

    # -- Serialization interface (subclasses override) ----------------------

    def to_dict(self) -> dict:
        """Return a plain dictionary representation of this entity.

        Raises:
            NotImplementedError: Always – subclasses must override.
        """
        raise NotImplementedError("to_dict() alt sınıfta tanımlanmalıdır.")

    @classmethod
    def from_dict(cls, data: dict):
        """Reconstruct an entity from a plain dictionary.

        Args:
            data: Dictionary previously produced by ``to_dict``.

        Raises:
            NotImplementedError: Always – subclasses must override.
        """
        raise NotImplementedError("from_dict() alt sınıfta tanımlanmalıdır.")

    # -- Representation -----------------------------------------------------

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
