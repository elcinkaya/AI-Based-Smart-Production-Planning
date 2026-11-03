"""
export.py - File export (.npz, CSV) and the Mini Project 3 record bridge.

Implements Section 5 (Kişi C) of the Mini Project 4 plan:
- save_simulation_npz / load_simulation_npz: array format; the
  configuration is stored as JSON text inside the archive.
- save_simulation_csv: long format, one row per machine-day (UTF-8,
  header row, ISO dates, full precision).
- split_units: integer split with the remainder on the first parts.
- simulation_to_records: converts machine-day totals into MP3
  ProductionRecord objects (one per shift) while preserving the totals.

No print/input is used; error messages are Turkish.  Input arrays are
never modified.

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import zipfile

import numpy as np

from capacity_simulation.models import SimulationConfig, SimulationResult
from production_records.record import SHIFT_HOURS, ProductionRecord, Shift

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Column order of the long-format CSV (Section 5).
CSV_COLUMNS: tuple[str, ...] = (
    "production_date",
    "machine_id",
    "efficiency_pct",
    "effective_capacity",
    "planned_units",
    "actual_units",
    "downtime_hours",
)

#: Array keys stored in the .npz archive (attribute names of SimulationResult).
NPZ_ARRAY_KEYS: tuple[str, ...] = (
    "theoretical_capacity",
    "efficiency_pct",
    "effective_capacity",
    "planned_units",
    "downtime_hours",
    "actual_units",
)

#: Key of the JSON configuration text inside the .npz archive.
NPZ_CONFIG_KEY: str = "config"

#: Shift order used when a machine-day is split into shifts (MP3 rule).
SHIFT_SEQUENCE: tuple[Shift, ...] = (Shift.MORNING, Shift.AFTERNOON, Shift.NIGHT)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_result(result) -> SimulationResult:
    """Ensure *result* is a SimulationResult.

    Raises:
        TypeError: If *result* is not a SimulationResult.
    """
    if not isinstance(result, SimulationResult):
        raise TypeError("result bir SimulationResult nesnesi olmalıdır.")
    return result


def _validate_path(path) -> str:
    """Ensure *path* is a non-empty string.

    Raises:
        TypeError: If *path* is not a string.
        ValueError: If *path* is empty.
    """
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError("Dosya yolu (path) metin (str) olmalıdır.")
    text = os.fspath(path)
    if not text.strip():
        raise ValueError("Dosya yolu (path) boş olamaz.")
    return text


def _ensure_parent_dir(path: str) -> None:
    """Create the parent directory of *path* if it does not exist."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def _validate_int(value, field_name: str, lower: int) -> int:
    """Validate an integer (bool rejected, NumPy integers accepted) >= *lower*.

    Raises:
        TypeError: If *value* is not an integer.
        ValueError: If *value* is below *lower*.
    """
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{field_name} tam sayı (int) olmalıdır.")
    if value < lower:
        raise ValueError(f"{field_name} {lower} veya daha büyük olmalıdır.")
    return int(value)


def _line_products(factory: dict) -> tuple[dict, list]:
    """Return ``{line_id: sorted compatible codes}`` and all sorted product codes."""
    line_products = {}
    for line in factory.get("lines", []):
        data = line.to_dict() if hasattr(line, "to_dict") else line
        if not isinstance(data, dict):
            raise TypeError("Fabrika hatları ProductionLine nesnesi veya sözlük olmalıdır.")
        line_products[data["line_id"]] = sorted(data.get("compatible_product_codes", []))
    all_codes = sorted(
        p.product_code if hasattr(p, "product_code") else p["product_code"]
        for p in factory.get("products", [])
    )
    return line_products, all_codes


def _machine_products(factory: dict, machine_ids: list) -> list:
    """Return the sorted product list of every machine (MP3 generate_records rule).

    A machine uses the sorted compatible product codes of its line; if the
    line has none, all product codes of the factory are used.

    Raises:
        ValueError: If a machine is missing from the factory or no product
            can be assigned.
    """
    machines = {}
    for machine in factory.get("machines", []):
        machine_id = machine.machine_id if hasattr(machine, "machine_id") else machine["machine_id"]
        machines[machine_id] = machine
    line_products, all_codes = _line_products(factory)

    products = []
    for machine_id in machine_ids:
        if machine_id not in machines:
            raise ValueError(f"'{machine_id}' makinesi fabrika verisinde bulunamadı.")
        machine = machines[machine_id]
        line_id = machine.line_id if hasattr(machine, "line_id") else machine.get("line_id")
        codes = line_products.get(line_id) or all_codes
        if not codes:
            raise ValueError(f"'{machine_id}' makinesi için atanabilecek uyumlu ürün bulunamadı.")
        products.append(codes)
    return products


# ---------------------------------------------------------------------------
# NPZ
# ---------------------------------------------------------------------------

def save_simulation_npz(path: str, result: SimulationResult) -> None:
    """Save a simulation result as a NumPy ``.npz`` archive (``np.savez``).

    The archive contains the six SimulationResult arrays under their
    attribute names and the configuration as JSON text under ``config``.
    ``np.savez`` appends ``.npz`` if *path* has no such extension.

    Args:
        path: Target file path (parent folders are created).
        result: SimulationResult to save.

    Raises:
        TypeError: If *result* is not a SimulationResult or *path* is not str.
        ValueError: If *path* is empty.
    """
    res = _validate_result(result)
    target = _validate_path(path)
    _ensure_parent_dir(target)
    arrays = {name: getattr(res, name) for name in NPZ_ARRAY_KEYS}
    config_text = json.dumps(res.config.to_dict(), ensure_ascii=False)
    np.savez(target, **{NPZ_CONFIG_KEY: np.array(config_text)}, **arrays)


def load_simulation_npz(path: str) -> SimulationResult:
    """Load a SimulationResult saved by ``save_simulation_npz``.

    Pickled objects are never loaded (``allow_pickle=False``).

    Args:
        path: Path of the ``.npz`` file.

    Returns:
        The validated SimulationResult (``equals`` the saved one).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is corrupt, a key is missing or the stored
            data violates the SimulationResult contract.
    """
    source = _validate_path(path)
    if not os.path.isfile(source):
        raise FileNotFoundError(f"NPZ dosyası bulunamadı: {source}")
    try:
        with np.load(source, allow_pickle=False) as archive:
            missing = [k for k in (NPZ_CONFIG_KEY,) + NPZ_ARRAY_KEYS if k not in archive.files]
            if missing:
                raise ValueError(f"NPZ dosyası eksik: {', '.join(missing)} anahtar(lar)ı bulunamadı.")
            config_text = str(archive[NPZ_CONFIG_KEY][()])
            arrays = {name: np.array(archive[name]) for name in NPZ_ARRAY_KEYS}
    except ValueError as err:
        if str(err).startswith("NPZ dosyası eksik"):
            raise
        raise ValueError(f"NPZ dosyası bozuk veya okunamıyor: {source}") from err
    except (OSError, EOFError, zipfile.BadZipFile, KeyError) as err:
        raise ValueError(f"NPZ dosyası bozuk veya okunamıyor: {source}") from err

    try:
        config = SimulationConfig.from_dict(json.loads(config_text))
        return SimulationResult(config=config, **arrays)
    except (TypeError, ValueError) as err:
        raise ValueError(f"NPZ dosyasındaki veriler geçersiz: {err}") from err


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def save_simulation_csv(path: str, result: SimulationResult) -> None:
    """Save a simulation result as a long-format CSV file.

    One row per machine-day, sorted by day and then machine (config
    order). Columns: production_date, machine_id, efficiency_pct,
    effective_capacity, planned_units, actual_units, downtime_hours.
    production_date is ``start_date + day index`` (ISO); floats are written
    with full precision (shortest round-trip repr), nothing is rounded.

    Args:
        path: Target file path (parent folders are created).
        result: SimulationResult with (M, D) matrices.

    Raises:
        TypeError: If *result* is not a SimulationResult or *path* is not str.
        ValueError: If *path* is empty.
    """
    res = _validate_result(result)
    target = _validate_path(path)
    machine_count, day_count = res.get_shape()

    # (M, D) -> (D, M) -> flat: day-major order, machines inside each day.
    start = np.datetime64(res.config.start_date, "D")
    dates = np.repeat(start + np.arange(day_count), machine_count).astype(str).tolist()
    machine_ids = np.tile(np.array(res.config.machine_ids), day_count).tolist()
    columns = [
        dates,
        machine_ids,
        res.efficiency_pct.T.ravel().tolist(),
        res.effective_capacity.T.ravel().tolist(),
        res.planned_units.T.ravel().tolist(),
        res.actual_units.T.ravel().tolist(),
        res.downtime_hours.T.ravel().tolist(),
    ]

    _ensure_parent_dir(target)
    with open(target, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(zip(*columns))


# ---------------------------------------------------------------------------
# MP3 bridge
# ---------------------------------------------------------------------------

def split_units(total: int, parts: int) -> list[int]:
    """Split an integer quantity into *parts* integers; remainder goes first.

    Examples: ``split_units(577, 2) == [289, 288]``,
    ``split_units(5, 3) == [2, 2, 1]``.

    Args:
        total: Quantity to split (int >= 0).
        parts: Number of parts (int >= 1).

    Returns:
        List of *parts* Python ints whose sum is *total*.

    Raises:
        TypeError: If an argument is not an integer.
        ValueError: If total < 0 or parts < 1.
    """
    total_value = _validate_int(total, "total", 0)
    part_count = _validate_int(parts, "parts", 1)
    base, remainder = divmod(total_value, part_count)
    return [base + 1] * remainder + [base] * (part_count - remainder)


def simulation_to_records(result: SimulationResult, factory: dict) -> list[ProductionRecord]:
    """Convert a simulation into MP3 ProductionRecord objects (one per shift).

    Rules (Section 5):
    - shift count = working_hours / SHIFT_HOURS and must be an integer
      (8, 16 or 24 hours), otherwise ValueError;
    - shifts are morning, afternoon, night in this order;
    - product = sorted compatible product codes of the machine's line,
      rotated by day index (MP3 generate_records rule);
    - planned_units and actual_units are split with ``split_units``;
      downtime_hours is split equally;
    - a shift with planned_units 0 raises ValueError;
    - record_id stays None (assigned by ``RecordStore.add_records``).

    Records are ordered by day, then machine (config order), then shift.
    Total planned, actual and downtime values are preserved.

    Args:
        result: SimulationResult with (M, D) matrices.
        factory: ``load_factory_json`` output (machines, lines, products).

    Returns:
        List of ProductionRecord objects.

    Raises:
        TypeError: If *result* is not a SimulationResult or *factory* is
            not a dict.
        ValueError: If a shift count is not an integer, a machine is not in
            the factory or a shift would get 0 planned units.
    """
    res = _validate_result(result)
    if not isinstance(factory, dict):
        raise TypeError("Fabrika verisi bir sözlük (dict) olmalıdır.")
    config = res.config

    # Vectorized shift-count check for every machine.
    hours = np.array(config.working_hours, dtype=np.float64)
    shift_counts = hours / SHIFT_HOURS
    invalid = ~np.isclose(shift_counts, np.rint(shift_counts)) | (np.rint(shift_counts) < 1)
    if np.any(invalid):
        bad = [f"{mid} ({h:g} saat)" for mid, h, b in zip(config.machine_ids, hours, invalid) if b]
        raise ValueError(
            "Vardiya sayısı tam sayı değil; working_hours 8, 16 veya 24 saat olmalıdır: "
            + ", ".join(bad)
        )
    shift_counts = np.rint(shift_counts).astype(np.int64).tolist()
    products = _machine_products(factory, config.machine_ids)

    # Per-shift downtime is computed once, vectorized: (M, D) / (M, 1).
    shift_downtime = (res.downtime_hours / np.array(shift_counts, dtype=np.float64)[:, None]).tolist()
    planned = res.planned_units.tolist()
    actual = res.actual_units.tolist()
    start = datetime.date.fromisoformat(config.start_date)

    records = []
    for day in range(config.days):
        production_date = start + datetime.timedelta(days=day)
        for m, machine_id in enumerate(config.machine_ids):
            count = shift_counts[m]
            planned_parts = split_units(planned[m][day], count)
            if 0 in planned_parts:
                raise ValueError(
                    f"{machine_id} makinesi {production_date.isoformat()} gününde "
                    f"planlanan üretim ({planned[m][day]}) {count} vardiyaya bölünemiyor; "
                    "bir vardiyada planned_units 0 olamaz."
                )
            actual_parts = split_units(actual[m][day], count)
            product_code = products[m][day % len(products[m])]
            for shift, plan_part, actual_part in zip(SHIFT_SEQUENCE, planned_parts, actual_parts):
                records.append(
                    ProductionRecord(
                        production_date=production_date,
                        shift=shift,
                        machine_id=machine_id,
                        product_code=product_code,
                        planned_units=plan_part,
                        actual_units=actual_part,
                        downtime_hours=shift_downtime[m][day],
                        record_id=None,
                    )
                )
    return records
