"""
masters.py - Machine and product master tables (plan Sections 3.2 and 5).

- build_machine_master: one row per factory machine with the capacity
  columns.  Capacities are computed only with the vectorized MP4 functions
  ``calculate_theoretical_capacity_array`` and
  ``calculate_effective_capacity_array`` (MP1 formulas); no capacity formula
  is repeated here.
- build_product_master: one row per factory product.

Rules:
- ``factory`` is the ``load_factory_json`` output (MP2): a dict with the keys
  'products', 'machines', 'lines' holding Product / Machine objects.
- Rows keep the factory order; the index is 0..n-1.
- Capacities use the machine base efficiency (efficiency_pct) and ignore the
  machine status (same rule as the MP3/MP4 generators); ``is_available`` is
  only reported.
- shift_count = max(1, round(working_hours / SHIFT_HOURS)) (MP3 rule);
  shift_effective_capacity = effective_capacity / shift_count.
- Text columns use the pandas ``"string"`` dtype (missing value <NA>).
- No print/input; error messages are Turkish.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)
from production_analysis.schema import (
    MACHINE_MASTER_COLUMNS,
    PRODUCT_MASTER_COLUMNS,
    SHIFT_HOURS,
)

_MACHINE_ATTRIBUTES = (
    "machine_id",
    "name",
    "line_id",
    "working_hours",
    "cycle_time_sec",
    "efficiency_pct",
    "is_available",
)
_PRODUCT_ATTRIBUTES = ("product_code", "name", "processing_time_sec", "priority")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_factory_items(factory: dict, key: str, attributes: tuple, label: str) -> list:
    """Return ``factory[key]`` after checking the type of the container and items.

    Args:
        factory: ``load_factory_json`` output.
        key: 'machines' or 'products'.
        attributes: Attribute names every item must provide.
        label: Turkish name of the item type used in messages.

    Returns:
        The list of factory objects.

    Raises:
        TypeError: If *factory* is not a dict, ``factory[key]`` is not a list
            or an item lacks a required attribute.
        ValueError: If the key is missing or the list is empty.
    """
    if not isinstance(factory, dict):
        raise TypeError("Fabrika verisi bir sözlük (dict) olmalıdır (load_factory_json çıktısı).")
    if key not in factory:
        raise ValueError(f"Fabrika verisinde '{key}' anahtarı bulunamadı.")
    items = factory[key]
    if not isinstance(items, list):
        raise TypeError(f"Fabrika verisindeki '{key}' bir liste (list) olmalıdır.")
    if not items:
        raise ValueError(f"Fabrika verisinde hiç {label} bulunmuyor.")
    for position, item in enumerate(items):
        missing = [name for name in attributes if not hasattr(item, name)]
        if missing:
            raise TypeError(
                f"Fabrika verisindeki {position}. {label} nesnesinde eksik özellik: "
                f"{', '.join(missing)} (load_factory_json çıktısı beklenir)."
            )
    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_machine_master(factory: dict) -> pd.DataFrame:
    """Build the machine master table of all factory machines.

    Columns (in this order) and dtypes:
        machine_id (string), name (string), line_id (string, <NA> if the
        machine has no line), working_hours (float64, hours/day),
        cycle_time_sec (float64, seconds/unit), efficiency_pct (float64,
        percent), is_available (bool, MP2 ``Machine.is_available()``),
        shift_count (int64), theoretical_capacity (float64, units/day),
        effective_capacity (float64, units/day), shift_effective_capacity
        (float64, units/shift).

    Args:
        factory: ``load_factory_json`` output (machines are MP2 Machine objects).

    Returns:
        New DataFrame, one row per machine in factory order, index 0..n-1.

    Raises:
        TypeError: If *factory* is not a dict or a machine is not a Machine-like
            object.
        ValueError: If there are no machines or a machine value is outside the
            MP1 capacity rules (raised by the MP4 capacity functions).
    """
    machines = _get_factory_items(factory, "machines", _MACHINE_ATTRIBUTES, "makine")

    # Collecting attributes from the factory objects (not a DataFrame loop).
    working_hours = np.array([m.working_hours for m in machines], dtype=np.float64)
    cycle_time_sec = np.array([m.cycle_time_sec for m in machines], dtype=np.float64)
    efficiency_pct = np.array([m.efficiency_pct for m in machines], dtype=np.float64)

    # MP4 vectorized capacity: (M,) theoretical, efficiency as (M, 1) -> (M, 1).
    theoretical = calculate_theoretical_capacity_array(working_hours, cycle_time_sec)
    effective = calculate_effective_capacity_array(theoretical, efficiency_pct[:, None]).ravel()

    # MP3 rule: shift_count = max(1, round(working_hours / SHIFT_HOURS)).
    shift_count = np.maximum(1, np.rint(working_hours / SHIFT_HOURS)).astype(np.int64)
    shift_effective = effective / shift_count

    master = pd.DataFrame(
        {
            "machine_id": pd.array([m.machine_id for m in machines], dtype="string"),
            "name": pd.array([m.name for m in machines], dtype="string"),
            "line_id": pd.array([m.line_id for m in machines], dtype="string"),
            "working_hours": working_hours,
            "cycle_time_sec": cycle_time_sec,
            "efficiency_pct": efficiency_pct,
            "is_available": np.array([bool(m.is_available()) for m in machines], dtype=bool),
            "shift_count": shift_count,
            "theoretical_capacity": theoretical,
            "effective_capacity": effective,
            "shift_effective_capacity": shift_effective,
        },
        columns=MACHINE_MASTER_COLUMNS,
    )
    return master


def build_product_master(factory: dict) -> pd.DataFrame:
    """Build the product master table of all factory products.

    Columns (in this order) and dtypes:
        product_code (string), name (string), processing_time_sec (float64,
        seconds/unit), priority (int64, 1 = highest).

    Args:
        factory: ``load_factory_json`` output (products are MP2 Product objects).

    Returns:
        New DataFrame, one row per product in factory order, index 0..n-1.

    Raises:
        TypeError: If *factory* is not a dict or a product is not a
            Product-like object.
        ValueError: If there are no products.
    """
    products = _get_factory_items(factory, "products", _PRODUCT_ATTRIBUTES, "ürün")
    master = pd.DataFrame(
        {
            "product_code": pd.array([p.product_code for p in products], dtype="string"),
            "name": pd.array([p.name for p in products], dtype="string"),
            "processing_time_sec": np.array(
                [p.processing_time_sec for p in products], dtype=np.float64
            ),
            "priority": np.array([p.priority for p in products], dtype=np.int64),
        },
        columns=PRODUCT_MASTER_COLUMNS,
    )
    return master
