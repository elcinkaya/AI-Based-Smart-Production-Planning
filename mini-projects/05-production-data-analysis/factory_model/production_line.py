"""
production_line.py – ProductionLine entity and helper for the factory model.

A ProductionLine groups machines together and tracks which products
can be manufactured on the line.  Capacity is the sum of available
machines' effective capacities (parallel operation assumption).

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

from factory_model.base import FactoryEntity, validate_non_empty_str
from factory_model.machine import Machine
from factory_model.product import Product


class ProductionLine(FactoryEntity):
    """A production line that owns machines and has compatible products.

    Machines on the same line operate in parallel: line capacity equals
    the sum of the effective capacities of available machines.

    Attributes:
        line_id: Unique line identifier (e.g. ``'L1'``).
        name: Human-readable display name.
        machines: Internal list of Machine objects assigned to this line.
        compatible_product_codes: Set of product codes this line can produce.
    """

    _REQUIRED_FIELDS: tuple[str, ...] = (
        "line_id",
        "name",
        "machine_ids",
        "compatible_product_codes",
    )

    def __init__(self, line_id: str, name: str) -> None:
        """Create a new ProductionLine.

        Args:
            line_id: Unique identifier, non-empty string.
            name: Display name, non-empty string.

        Raises:
            TypeError: If any argument has the wrong type.
            ValueError: If any argument is empty or whitespace-only.
        """
        super().__init__(name)
        self._line_id: str = validate_non_empty_str(line_id, "line_id")
        self._machines: list[Machine] = []
        self._compatible_product_codes: set[str] = set()

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #

    @property
    def line_id(self) -> str:
        """Unique line identifier."""
        return self._line_id

    # ------------------------------------------------------------------ #
    # Machine management
    # ------------------------------------------------------------------ #

    def add_machine(self, machine: Machine) -> None:
        """Add a machine to this production line.

        Sets the machine's ``line_id`` to this line.

        Args:
            machine: Machine instance to add.

        Raises:
            TypeError: If *machine* is not a Machine instance.
            ValueError: If the machine is already in this line or belongs
                to another line.
        """
        if not isinstance(machine, Machine):
            raise TypeError("Hatta yalnızca Machine nesnesi eklenebilir.")

        # Check if machine already exists in this line
        for m in self._machines:
            if m.machine_id == machine.machine_id:
                raise ValueError(
                    f"'{machine.machine_id}' zaten bu hatta mevcut."
                )

        # Check if machine belongs to another line
        if machine.line_id is not None and machine.line_id != self._line_id:
            raise ValueError(
                f"'{machine.machine_id}' başka bir hatta "
                f"('{machine.line_id}') bağlı."
            )

        machine.line_id = self._line_id
        self._machines.append(machine)

    def remove_machine(self, machine_id: str) -> Machine:
        """Remove a machine from this line by its ID.

        Sets the machine's ``line_id`` to None.

        Args:
            machine_id: ID of the machine to remove.

        Returns:
            The removed Machine instance.

        Raises:
            ValueError: If no machine with *machine_id* is found.
        """
        for i, m in enumerate(self._machines):
            if m.machine_id == machine_id:
                removed = self._machines.pop(i)
                removed.line_id = None
                return removed
        raise ValueError(f"Bu hatta '{machine_id}' kimlikli makine bulunamadı.")

    def get_machine(self, machine_id: str) -> Machine:
        """Retrieve a machine from this line by its ID.

        Args:
            machine_id: ID of the machine to find.

        Returns:
            The matching Machine instance.

        Raises:
            ValueError: If no machine with *machine_id* is found.
        """
        for m in self._machines:
            if m.machine_id == machine_id:
                return m
        raise ValueError(f"Bu hatta '{machine_id}' kimlikli makine bulunamadı.")

    # ------------------------------------------------------------------ #
    # Product compatibility
    # ------------------------------------------------------------------ #

    def add_compatible_product(self, product: Product) -> None:
        """Register a product as compatible with this line.

        Stores only the product's ``product_code``; the Product object
        itself is not retained (avoids circular references).

        Args:
            product: Product instance whose code will be stored.

        Raises:
            TypeError: If *product* is not a Product instance.
        """
        if not isinstance(product, Product):
            raise TypeError(
                "Uyumlu ürün olarak yalnızca Product nesnesi eklenebilir."
            )
        self._compatible_product_codes.add(product.product_code)

    def is_compatible(self, product: Product) -> bool:
        """Check whether a product is compatible with this line.

        Args:
            product: Product instance to check.

        Returns:
            True if the product's code is in the compatible set.
        """
        return product.product_code in self._compatible_product_codes

    # ------------------------------------------------------------------ #
    # Capacity and maintenance queries
    # ------------------------------------------------------------------ #

    def get_available_machines(self) -> list[Machine]:
        """Return machines that are currently available (IDLE or RUNNING).

        Returns:
            List of available Machine instances.
        """
        return [m for m in self._machines if m.is_available()]

    def get_effective_capacity(self, product: Product | None = None) -> float:
        """Calculate total effective capacity of this line.

        When *product* is None, each machine uses its own default
        cycle time.  When a product is given, its ``processing_time_sec``
        is used as the cycle time for every available machine.

        Args:
            product: Optional product for product-specific capacity.

        Returns:
            Sum of available machines' effective capacities (units/day).

        Raises:
            ValueError: If *product* is given but is not compatible
                with this line.
        """
        if product is not None and not self.is_compatible(product):
            raise ValueError(
                f"'{product.product_code}' ürünü bu hat "
                f"('{self._line_id}') ile uyumlu değil."
            )

        total = 0.0
        for m in self._machines:
            if product is not None:
                total += m.get_effective_capacity(
                    cycle_time_sec=product.processing_time_sec
                )
            else:
                total += m.get_effective_capacity()
        return total

    def get_machines_needing_maintenance(self) -> list[Machine]:
        """Return machines on this line that need maintenance.

        Returns:
            List of Machine instances where ``needs_maintenance()`` is True.
        """
        return [m for m in self._machines if m.needs_maintenance()]

    # ------------------------------------------------------------------ #
    # Serialization (Section 3.4 data contract)
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Convert line to a dictionary matching the Section 3.4 contract.

        Returns:
            Dictionary with keys: line_id, name, machine_ids (list),
            compatible_product_codes (sorted list).
        """
        return {
            "line_id": self._line_id,
            "name": self.name,
            "machine_ids": [m.machine_id for m in self._machines],
            "compatible_product_codes": sorted(self._compatible_product_codes),
        }

    @classmethod
    def from_dict(
        cls, data: dict, machines_by_id: dict[str, Machine],
    ) -> ProductionLine:
        """Create a ProductionLine from a dictionary and a machine lookup.

        Args:
            data: Dictionary with keys ``line_id``, ``name``,
                ``machine_ids``, ``compatible_product_codes``.
            machines_by_id: Mapping from machine_id to Machine instances.

        Returns:
            A new ProductionLine with machines added and compatible
            product codes set.

        Raises:
            ValueError: If a required key is missing from *data* or if a
                machine_id is not found in *machines_by_id*.
        """
        for field in cls._REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Eksik alan: {field}")

        line = cls(line_id=data["line_id"], name=data["name"])

        # Add machines
        for mid in data["machine_ids"]:
            if mid not in machines_by_id:
                raise ValueError(
                    f"'{mid}' kimlikli makine machines_by_id içinde bulunamadı."
                )
            machine = machines_by_id[mid]
            line.add_machine(machine)

        # Set compatible product codes directly (no Product objects
        # available during deserialization)
        for code in data["compatible_product_codes"]:
            line._compatible_product_codes.add(code)

        return line

    # ------------------------------------------------------------------ #
    # Representation
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        machine_ids = [m.machine_id for m in self._machines]
        return (
            f"ProductionLine(line_id={self._line_id!r}, "
            f"name={self.name!r}, "
            f"machines={machine_ids!r}, "
            f"compatible_products="
            f"{sorted(self._compatible_product_codes)!r})"
        )


# ====================================================================== #
# Module-level helper
# ====================================================================== #

def find_lines_for_product(
    product: Product, lines: list[ProductionLine],
) -> list[ProductionLine]:
    """Find all production lines that can produce a given product.

    Args:
        product: Product to search for.
        lines: List of ProductionLine instances to search.

    Returns:
        List of lines compatible with the product.
    """
    return [ln for ln in lines if ln.is_compatible(product)]
