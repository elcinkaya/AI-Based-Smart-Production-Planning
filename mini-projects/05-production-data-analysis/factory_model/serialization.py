"""
serialization.py – JSON and CSV import/export for the factory model.

Provides functions to serialize collections of Products, Machines, and
ProductionLines to JSON files and to export machine data to CSV.

Design note: Machine and ProductionLine classes are not yet implemented
(owned by Kişi B and Kişi C).  Until integration, this module works with
any object that exposes ``to_dict()`` and the corresponding
``from_dict(data)`` class method.  After integration the stub references
will be replaced with real imports.

Author: Kişi A
Mini Project: 02 – Factory Object Model
"""
from __future__ import annotations

import csv
import json
from typing import Any

from factory_model.product import Product

# ---------------------------------------------------------------------------
# Conditional imports – Machine and ProductionLine may not exist yet.
# When they are available they will be imported; until then the
# deserialization helpers that require them will raise clear errors.
# ---------------------------------------------------------------------------
try:
    from factory_model.machine import Machine  # Kişi B
except ImportError:
    Machine = None  # type: ignore[assignment,misc]

try:
    from factory_model.production_line import ProductionLine  # Kişi C
except ImportError:
    ProductionLine = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Dict helpers
# ---------------------------------------------------------------------------

def factory_to_dict(
    products: list,
    machines: list,
    lines: list,
) -> dict:
    """Convert full factory data into a plain dictionary.

    Args:
        products: List of Product instances (or any objects with ``to_dict``).
        machines: List of Machine instances (or any objects with ``to_dict``).
        lines: List of ProductionLine instances (or any objects with
            ``to_dict``).

    Returns:
        Dictionary with keys ``'products'``, ``'machines'``, ``'lines'``,
        each containing a list of dictionaries.
    """
    return {
        "products": [p.to_dict() for p in products],
        "machines": [m.to_dict() for m in machines],
        "lines": [ln.to_dict() for ln in lines],
    }


def factory_from_dict(data: dict) -> dict:
    """Reconstruct factory objects from a plain dictionary.

    Build order: products → machines → lines (lines need *machines_by_id*).

    Args:
        data: Dictionary with keys ``'products'``, ``'machines'``,
            ``'lines'``, each containing a list of dictionaries as
            produced by ``factory_to_dict``.

    Returns:
        Dictionary with keys ``'products'``, ``'machines'``, ``'lines'``,
        each containing a list of the corresponding domain objects.

    Raises:
        RuntimeError: If Machine or ProductionLine classes are not yet
            available (modules not implemented / imported).
        ValueError: Propagated from ``from_dict`` of individual classes.
    """
    # -- Products -----------------------------------------------------------
    products = [Product.from_dict(d) for d in data.get("products", [])]

    # -- Machines -----------------------------------------------------------
    raw_machines = data.get("machines", [])
    if raw_machines and Machine is None:
        raise RuntimeError(
            "Machine sınıfı henüz mevcut değil. "
            "Kişi B'nin machine.py modülünü tamamlaması bekleniyor."
        )
    machines = (
        [Machine.from_dict(d) for d in raw_machines]
        if Machine is not None
        else []
    )

    # -- Lines --------------------------------------------------------------
    raw_lines = data.get("lines", [])
    if raw_lines and ProductionLine is None:
        raise RuntimeError(
            "ProductionLine sınıfı henüz mevcut değil. "
            "Kişi C'nin production_line.py modülünü tamamlaması bekleniyor."
        )
    machines_by_id: dict[str, Any] = {m.machine_id: m for m in machines}
    lines = (
        [ProductionLine.from_dict(d, machines_by_id) for d in raw_lines]
        if ProductionLine is not None
        else []
    )

    return {
        "products": products,
        "machines": machines,
        "lines": lines,
    }


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------

def save_factory_json(
    path: str,
    products: list,
    machines: list,
    lines: list,
) -> None:
    """Save factory data to a JSON file.

    Args:
        path: Destination file path.
        products: List of Product instances.
        machines: List of Machine instances.
        lines: List of ProductionLine instances.
    """
    payload = factory_to_dict(products, machines, lines)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def load_factory_json(path: str) -> dict:
    """Load factory data from a JSON file.

    Args:
        path: Source file path.

    Returns:
        Same shape as ``factory_from_dict`` – a dictionary with keys
        ``'products'``, ``'machines'``, ``'lines'``, each containing
        domain objects.

    Raises:
        RuntimeError: If Machine or ProductionLine classes are not yet
            available.
        FileNotFoundError: If *path* does not exist.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return factory_from_dict(data)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

_MACHINE_CSV_HEADERS = [
    "machine_id",
    "name",
    "working_hours",
    "cycle_time_sec",
    "efficiency_pct",
    "maintenance_interval_hours",
    "status",
    "operating_hours_since_maintenance",
    "line_id",
]


def export_machines_csv(path: str, machines: list) -> None:
    """Export a list of machines to a flat CSV file.

    Each machine is written as one row.  The column order follows the
    data-contract attribute order defined in the project plan (section
    3.4).

    Args:
        path: Destination file path.
        machines: List of Machine instances (or any objects whose
            ``to_dict`` returns the machine-contract keys).
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_MACHINE_CSV_HEADERS)
        writer.writeheader()
        for machine in machines:
            row = machine.to_dict()
            writer.writerow({k: row.get(k, "") for k in _MACHINE_CSV_HEADERS})
