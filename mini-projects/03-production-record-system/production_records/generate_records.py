"""
generate_records.py – Deterministic synthetic production records generator.

This module generates reproducible synthetic production records based on a
factory configuration dictionary (products, machines, lines).

Rules:
- Uses an isolated random.Random(seed) instance for reproducibility.
- Skips unavailable machines (e.g. BROKEN or MAINTENANCE).
- Determines daily shifts: max(1, round(working_hours / SHIFT_HOURS)).
- Shifts assigned in order: MORNING, AFTERNOON, NIGHT.
- Computes shift capacity using Mini Project 1 calculations.
- Rotates compatible product codes by calendar day index.
- Planned units: round(shift_capacity * uniform(0.80, 1.00)).
- Downtime hours: 30% chance of round(uniform(0.25, 3.0) * 4) / 4, else 0.0.
- Actual units: max(0, round(planned_units * uniform(0.90, 1.05) * (1 - downtime / 8))).

Author: Kişi A
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
import random
from typing import Any

from production_records.record import SHIFT_HOURS, Shift, ProductionRecord

try:
    from factory_model import calculations
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from factory_model import calculations


def generate_records(
    factory: dict[str, Any],
    start_date: str | datetime.date,
    days: int,
    seed: int = 42,
) -> list[ProductionRecord]:
    """Generate reproducible synthetic production records for a factory model.

    Args:
        factory: Dictionary with keys 'products', 'machines', 'lines'
            (as produced by factory_model.serialization.load_factory_json).
        start_date: Start date as ISO string (YYYY-MM-DD) or datetime.date.
        days: Number of consecutive days to generate records for (> 0).
        seed: Random seed for deterministic reproducibility (defaults to 42).

    Returns:
        List of ProductionRecord instances.

    Raises:
        TypeError: If arguments are of invalid types.
        ValueError: If days <= 0 or start_date is invalid.
    """
    if not isinstance(factory, dict):
        raise TypeError("Fabrika verisi bir sözlük (dict) olmalıdır.")

    if isinstance(days, bool) or not isinstance(days, int):
        raise TypeError("Gün sayısı (days) tam sayı olmalıdır.")
    if days <= 0:
        raise ValueError("Gün sayısı (days) sıfırdan büyük olmalıdır.")

    if isinstance(start_date, datetime.datetime):
        base_date = start_date.date()
    elif isinstance(start_date, datetime.date):
        base_date = start_date
    elif isinstance(start_date, str):
        try:
            base_date = datetime.date.fromisoformat(start_date.strip())
        except ValueError as err:
            raise ValueError(
                f"Geçersiz başlangıç tarihi: '{start_date}'. 'YYYY-MM-DD' olmalıdır."
            ) from err
    else:
        raise TypeError("Başlangıç tarihi (start_date) datetime.date veya ISO metin olmalıdır.")

    # Isolated RNG instance for deterministic reproducibility
    rng = random.Random(seed)

    # 1. Filter available machines
    raw_machines = factory.get("machines", [])
    available_machines: list[Any] = []
    for m in raw_machines:
        is_avail = False
        if hasattr(m, "is_available"):
            is_avail = m.is_available()
        elif isinstance(m, dict):
            status = m.get("status", "")
            is_avail = status in ("idle", "running")
        if is_avail:
            available_machines.append(m)

    # Sort machines by ID for deterministic iteration order
    available_machines.sort(
        key=lambda m: m.machine_id if hasattr(m, "machine_id") else m.get("machine_id", "")
    )

    # 2. Build line lookup and compatible products map
    raw_lines = factory.get("lines", [])
    line_lookup: dict[str, Any] = {}
    for ln in raw_lines:
        lid = ln.line_id if hasattr(ln, "line_id") else ln.get("line_id", "")
        if lid:
            line_lookup[lid] = ln

    # Fallback product codes if a line has no defined compatible products
    all_product_codes: list[str] = []
    for p in factory.get("products", []):
        pcode = p.product_code if hasattr(p, "product_code") else p.get("product_code", "")
        if pcode:
            all_product_codes.append(pcode)
    all_product_codes.sort()

    def get_compatible_products(machine: Any) -> list[str]:
        lid = machine.line_id if hasattr(machine, "line_id") else machine.get("line_id", "")
        if lid and lid in line_lookup:
            ln = line_lookup[lid]
            if hasattr(ln, "_compatible_product_codes"):
                return sorted(ln._compatible_product_codes)
            if hasattr(ln, "compatible_product_codes"):
                return sorted(ln.compatible_product_codes)
            if isinstance(ln, dict) and "compatible_product_codes" in ln:
                return sorted(ln["compatible_product_codes"])
        return all_product_codes

    records: list[ProductionRecord] = []

    shift_sequence = [Shift.MORNING, Shift.AFTERNOON, Shift.NIGHT]

    # 3. Generate records day by day
    for day_idx in range(days):
        current_date = base_date + datetime.timedelta(days=day_idx)

        for machine in available_machines:
            m_id = machine.machine_id if hasattr(machine, "machine_id") else machine.get("machine_id")
            w_hours = machine.working_hours if hasattr(machine, "working_hours") else machine.get("working_hours", 8.0)
            c_time = machine.cycle_time_sec if hasattr(machine, "cycle_time_sec") else machine.get("cycle_time_sec", 30.0)
            eff_pct = machine.efficiency_pct if hasattr(machine, "efficiency_pct") else machine.get("efficiency_pct", 80.0)

            # Determine number of shifts
            num_shifts = max(1, round(w_hours / SHIFT_HOURS))
            shifts_to_run = shift_sequence[:num_shifts]

            # Shift capacity: theoretical and effective capacity / num_shifts
            theo = calculations.theoretical_capacity(w_hours, c_time)
            eff = calculations.effective_capacity(theo, eff_pct)
            shift_capacity = eff / num_shifts

            # Rotate compatible products by day index
            comp_products = get_compatible_products(machine)
            if not comp_products:
                raise ValueError(f"'{m_id}' makinesi için atanabilecek uyumlu ürün bulunamadı.")
            product_code = comp_products[day_idx % len(comp_products)]

            for shift in shifts_to_run:
                # Planned units: round(shift_capacity * uniform(0.80, 1.00))
                factor_plan = rng.uniform(0.80, 1.00)
                planned_units = max(1, round(shift_capacity * factor_plan))

                # Downtime: 30% chance of round(uniform(0.25, 3.0) * 4) / 4, else 0.0
                if rng.random() < 0.30:
                    downtime_hours = round(rng.uniform(0.25, 3.0) * 4) / 4
                else:
                    downtime_hours = 0.0

                # Actual units: max(0, round(planned_units * uniform(0.90, 1.05) * (1 - downtime / 8)))
                factor_actual = rng.uniform(0.90, 1.05)
                actual_multiplier = max(0.0, 1.0 - (downtime_hours / SHIFT_HOURS))
                actual_units = max(
                    0,
                    round(planned_units * factor_actual * actual_multiplier)
                )

                record = ProductionRecord(
                    production_date=current_date,
                    shift=shift,
                    machine_id=m_id,
                    product_code=product_code,
                    planned_units=planned_units,
                    actual_units=actual_units,
                    downtime_hours=downtime_hours,
                    record_id=None,
                )
                records.append(record)

    return records
