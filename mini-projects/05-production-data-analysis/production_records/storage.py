"""
storage.py – CSV/JSON read, write, append and conversion utilities for production records.

This module provides stateless file I/O functions following the save_*/load_*
naming convention established in Mini Project 2.  All functions work with
ProductionRecord instances and enforce the data contract defined in Section 3.2
and the file operation rules from Section 3.3.

Functions:
    load_records_json  – Read all records from a JSON file.
    save_records_json  – Write records to a JSON file (atomic: temp + os.replace).
    append_record_json – Read-modify-write a single record to a JSON file.
    load_records_csv   – Read all records from a CSV file.
    save_records_csv   – Write all records to a CSV file (overwrite).
    append_record_csv  – Append a single record to a CSV file ('a' mode).
    convert_records_file – Convert between JSON and CSV formats.

Author: Kişi B
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import csv
import json
import os
from typing import Any

from production_records.record import ProductionRecord


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSV_COLUMNS: list[str] = [
    "record_id",
    "production_date",
    "shift",
    "machine_id",
    "product_code",
    "planned_units",
    "actual_units",
    "downtime_hours",
]

JSON_SCHEMA_VERSION: int = 1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_parent_dir(path: str) -> None:
    """Create parent directories for *path* if they do not exist."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _is_empty_file(path: str) -> bool:
    """Return True if *path* does not exist or has zero bytes."""
    if not os.path.exists(path):
        return True
    return os.path.getsize(path) == 0


def _csv_row_to_dict(row: dict[str, str], line_number: int, path: str) -> dict[str, Any]:
    """Convert a CSV DictReader row (all strings) to typed dict for from_dict.

    Raises:
        ValueError: If a field cannot be converted to its expected type.
    """
    try:
        typed: dict[str, Any] = {
            "record_id": int(row["record_id"]),
            "production_date": row["production_date"],
            "shift": row["shift"],
            "machine_id": row["machine_id"],
            "product_code": row["product_code"],
            "planned_units": int(row["planned_units"]),
            "actual_units": int(row["actual_units"]),
            "downtime_hours": float(row["downtime_hours"]),
        }
    except (ValueError, KeyError) as err:
        raise ValueError(
            f"'{path}' dosyasının {line_number}. satırında geçersiz veri: {err}"
        ) from err
    return typed


# ---------------------------------------------------------------------------
# JSON operations
# ---------------------------------------------------------------------------

def load_records_json(path: str) -> list[ProductionRecord]:
    """Load production records from a JSON file.

    If the file does not exist or is empty (0 bytes), returns an empty list.

    Args:
        path: File path with .json extension.

    Returns:
        List of ProductionRecord instances.

    Raises:
        ValueError: If the file contains invalid JSON, missing schema_version,
            or records that cannot be parsed.
    """
    if _is_empty_file(path):
        return []

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as err:
        raise ValueError(
            f"'{path}' dosyası geçersiz JSON içeriyor: {err}"
        ) from err

    if not isinstance(data, dict) or "records" not in data:
        raise ValueError(
            f"'{path}' dosyasında 'records' anahtarı bulunamadı."
        )

    raw_records = data["records"]
    records: list[ProductionRecord] = []
    for idx, item in enumerate(raw_records, start=1):
        try:
            records.append(ProductionRecord.from_dict(item))
        except (TypeError, ValueError) as err:
            raise ValueError(
                f"'{path}' dosyasının {idx}. kaydında hata: {err}"
            ) from err

    return records


def save_records_json(path: str, records: list[ProductionRecord] | None = None) -> None:
    """Write records to a JSON file atomically (temp file + os.replace).

    Args:
        path: Target file path.
        records: List of ProductionRecord instances to save.  If None, an
            empty list is used.

    Raises:
        TypeError: If any element in *records* is not a ProductionRecord.
    """
    if records is None:
        records = []

    for idx, rec in enumerate(records):
        if not isinstance(rec, ProductionRecord):
            raise TypeError(
                f"Kayıt listesinin {idx}. elemanı ProductionRecord türünde olmalıdır."
            )

    _ensure_parent_dir(path)

    payload: dict[str, Any] = {
        "schema_version": JSON_SCHEMA_VERSION,
        "records": [rec.to_dict() for rec in records],
    }

    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    os.replace(tmp_path, path)


def append_record_json(path: str, record: ProductionRecord) -> None:
    """Append a single record to a JSON file using read-modify-write.

    If the file does not exist, it is created.

    Args:
        path: Target JSON file path.
        record: The ProductionRecord to append.
    """
    if not isinstance(record, ProductionRecord):
        raise TypeError("Eklenecek kayıt ProductionRecord türünde olmalıdır.")

    existing = load_records_json(path)
    existing.append(record)
    save_records_json(path, existing)


# ---------------------------------------------------------------------------
# CSV operations
# ---------------------------------------------------------------------------

def load_records_csv(path: str) -> list[ProductionRecord]:
    """Load production records from a CSV file.

    If the file does not exist or is empty (0 bytes), returns an empty list.

    Args:
        path: File path with .csv extension.

    Returns:
        List of ProductionRecord instances.

    Raises:
        ValueError: If the header is missing/incorrect or any row is invalid.
    """
    if _is_empty_file(path):
        return []

    with open(path, encoding="utf-8", newline="") as fh:
        # Validate header
        first_line = fh.readline().rstrip("\r\n")
        expected_header = ",".join(CSV_COLUMNS)
        if first_line != expected_header:
            raise ValueError(
                f"'{path}' dosyasında beklenen başlık satırı bulunamadı. "
                f"Beklenen: '{expected_header}', Bulunan: '{first_line}'"
            )
        fh.seek(0)

        reader = csv.DictReader(fh)
        records: list[ProductionRecord] = []
        for line_number, row in enumerate(reader, start=2):
            typed = _csv_row_to_dict(row, line_number, path)
            try:
                records.append(ProductionRecord.from_dict(typed))
            except (TypeError, ValueError) as err:
                raise ValueError(
                    f"'{path}' dosyasının {line_number}. satırında geçersiz kayıt: {err}"
                ) from err

    return records


def save_records_csv(path: str, records: list[ProductionRecord] | None = None) -> None:
    """Write all records to a CSV file (overwrite).

    Args:
        path: Target file path.
        records: List of ProductionRecord instances.  If None, only the header
            is written.

    Raises:
        TypeError: If any element is not a ProductionRecord.
    """
    if records is None:
        records = []

    for idx, rec in enumerate(records):
        if not isinstance(rec, ProductionRecord):
            raise TypeError(
                f"Kayıt listesinin {idx}. elemanı ProductionRecord türünde olmalıdır."
            )

    _ensure_parent_dir(path)

    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.to_dict())


def append_record_csv(path: str, record: ProductionRecord) -> None:
    """Append a single record to a CSV file.

    Opens the file in 'a' mode so existing rows are never modified.
    If the file is new or empty, the header row is written first.

    Args:
        path: Target CSV file path.
        record: The ProductionRecord to append.

    Raises:
        TypeError: If record is not a ProductionRecord.
    """
    if not isinstance(record, ProductionRecord):
        raise TypeError("Eklenecek kayıt ProductionRecord türünde olmalıdır.")

    _ensure_parent_dir(path)

    write_header = _is_empty_file(path)

    with open(path, "a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(record.to_dict())


# ---------------------------------------------------------------------------
# Format conversion
# ---------------------------------------------------------------------------

def convert_records_file(source_path: str, target_path: str) -> int:
    """Convert production records between JSON and CSV formats.

    The source format is determined by the file extension (.json or .csv).
    The target must have the opposite extension.

    Args:
        source_path: Path to the source file (.json or .csv).
        target_path: Path to the target file (.csv or .json).

    Returns:
        The number of records converted.

    Raises:
        ValueError: If extensions are unsupported or identical.
    """
    src_ext = os.path.splitext(source_path)[1].lower()
    tgt_ext = os.path.splitext(target_path)[1].lower()

    if src_ext not in (".csv", ".json"):
        raise ValueError(
            f"Kaynak dosya uzantısı desteklenmiyor: '{src_ext}'. "
            "Desteklenen uzantılar: .csv, .json"
        )
    if tgt_ext not in (".csv", ".json"):
        raise ValueError(
            f"Hedef dosya uzantısı desteklenmiyor: '{tgt_ext}'. "
            "Desteklenen uzantılar: .csv, .json"
        )
    if src_ext == tgt_ext:
        raise ValueError(
            "Kaynak ve hedef dosya uzantıları aynı olamaz. "
            f"Her ikisi de '{src_ext}'."
        )

    # Load from source
    if src_ext == ".json":
        records = load_records_json(source_path)
    else:
        records = load_records_csv(source_path)

    # Save to target
    if tgt_ext == ".json":
        save_records_json(target_path, records)
    else:
        save_records_csv(target_path, records)

    return len(records)
