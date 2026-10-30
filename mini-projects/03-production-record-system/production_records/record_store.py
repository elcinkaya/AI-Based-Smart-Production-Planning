"""
record_store.py – High-level record management layer backed by CSV/JSON files.

RecordStore provides a repository-style API for adding, querying and filtering
production records.  It delegates all file I/O to the storage module and
enforces uniqueness, validation and ID assignment rules defined in the project
plan (Sections 3.2 and 3.3).

The public interface (add_record, get_all, filter_records, count) is designed
to be swappable with a database-backed implementation in Mini Project 9 without
changing calling code.

Author: Kişi B
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
import os
from typing import Any

from production_records.record import ProductionRecord, Shift
from production_records.storage import (
    load_records_csv,
    load_records_json,
    save_records_csv,
    save_records_json,
    append_record_csv,
    append_record_json,
)


class RecordStore:
    """Stateless file-backed production record repository.

    Each method reads from or writes to the underlying file directly;
    no in-memory cache is maintained.

    Attributes:
        path: Absolute or relative path to the backing file (.csv or .json).
        valid_machine_ids: Optional set of accepted machine IDs.
        valid_product_codes: Optional set of accepted product codes.
    """

    def __init__(
        self,
        path: str,
        valid_machine_ids: set[str] | None = None,
        valid_product_codes: set[str] | None = None,
    ) -> None:
        """Initialize the RecordStore.

        Args:
            path: Path to the data file (.csv or .json).
            valid_machine_ids: Optional whitelist of valid machine IDs.
                If None, any non-empty machine_id is accepted.
            valid_product_codes: Optional whitelist of valid product codes.
                If None, any non-empty product_code is accepted.

        Raises:
            ValueError: If the file extension is not .csv or .json.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".csv", ".json"):
            raise ValueError(
                f"Desteklenmeyen dosya uzantısı: '{ext}'. "
                "Yalnızca .csv ve .json dosyaları desteklenir."
            )

        self.path: str = path
        self._ext: str = ext
        self.valid_machine_ids: set[str] | None = (
            set(valid_machine_ids) if valid_machine_ids is not None else None
        )
        self.valid_product_codes: set[str] | None = (
            set(valid_product_codes) if valid_product_codes is not None else None
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[ProductionRecord]:
        """Load all records from the backing file."""
        if self._ext == ".json":
            return load_records_json(self.path)
        return load_records_csv(self.path)

    def _save(self, records: list[ProductionRecord]) -> None:
        """Overwrite the backing file with *records*."""
        if self._ext == ".json":
            save_records_json(self.path, records)
        else:
            save_records_csv(self.path, records)

    def _append(self, record: ProductionRecord) -> None:
        """Append a single record to the backing file."""
        if self._ext == ".json":
            append_record_json(self.path, record)
        else:
            append_record_csv(self.path, record)

    def _next_id(self, existing: list[ProductionRecord]) -> int:
        """Return the next available record_id.

        Rule: max(existing record_ids) + 1; 1 if the store is empty.
        """
        if not existing:
            return 1
        max_id = max(
            (r.record_id for r in existing if r.record_id is not None),
            default=0,
        )
        return max_id + 1

    def _validate_record(
        self,
        record: ProductionRecord,
        existing_keys: set[tuple[str, str, str]],
    ) -> None:
        """Validate a record before insertion.

        Checks:
        - Must be a ProductionRecord instance.
        - record_id must be None (not yet assigned).
        - Uniqueness key must not collide with existing records.
        - machine_id and product_code must be in valid sets (if provided).

        Raises:
            TypeError: If *record* is not a ProductionRecord.
            ValueError: If any validation rule is violated.
        """
        if not isinstance(record, ProductionRecord):
            raise TypeError(
                "Eklenecek kayıt ProductionRecord türünde olmalıdır."
            )

        if record.record_id is not None:
            raise ValueError(
                "Yeni kayıtın record_id değeri None olmalıdır; "
                "kayıt numarası depo tarafından atanır."
            )

        key = record.get_key()
        if key in existing_keys:
            raise ValueError(
                f"Mükerrer kayıt: ({key[0]}, {key[1]}, {key[2]}) "
                "kombinasyonu zaten mevcut."
            )

        if (
            self.valid_machine_ids is not None
            and record.machine_id not in self.valid_machine_ids
        ):
            raise ValueError(
                f"Geçersiz makine kimliği: '{record.machine_id}'. "
                f"Geçerli değerler: {sorted(self.valid_machine_ids)}"
            )

        if (
            self.valid_product_codes is not None
            and record.product_code not in self.valid_product_codes
        ):
            raise ValueError(
                f"Geçersiz ürün kodu: '{record.product_code}'. "
                f"Geçerli değerler: {sorted(self.valid_product_codes)}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_record(self, record: ProductionRecord) -> ProductionRecord:
        """Add a single record to the store.

        Assigns a unique record_id and appends the record to the file.

        Args:
            record: A ProductionRecord with record_id=None.

        Returns:
            The same ProductionRecord instance with record_id assigned.

        Raises:
            TypeError: If *record* is not a ProductionRecord.
            ValueError: If record_id is already set, key is duplicate,
                or machine_id/product_code is invalid.
        """
        existing = self._load()
        existing_keys = {r.get_key() for r in existing}

        self._validate_record(record, existing_keys)

        record.record_id = self._next_id(existing)
        self._append(record)

        return record

    def add_records(self, records: list[ProductionRecord] | None = None) -> list[ProductionRecord]:
        """Add multiple records atomically.

        All records are validated FIRST; if any record fails validation,
        NONE of them are written.

        Args:
            records: List of ProductionRecord instances with record_id=None.

        Returns:
            The list of records with record_ids assigned.

        Raises:
            TypeError: If any element is not a ProductionRecord.
            ValueError: If any validation rule is violated.
        """
        if records is None:
            records = []

        if not records:
            return []

        existing = self._load()
        existing_keys = {r.get_key() for r in existing}
        next_id = self._next_id(existing)

        # Phase 1: Validate ALL records before writing anything
        for idx, rec in enumerate(records):
            self._validate_record(rec, existing_keys)
            # Temporarily add key to detect duplicates within the batch
            existing_keys.add(rec.get_key())

        # Phase 2: Assign IDs and write
        for rec in records:
            rec.record_id = next_id
            next_id += 1

        all_records = existing + list(records)
        self._save(all_records)

        return list(records)

    def get_all(self) -> list[ProductionRecord]:
        """Return all records from the store.

        Returns:
            List of ProductionRecord instances (empty if file is missing).
        """
        return self._load()

    def get_record(self, record_id: int) -> ProductionRecord:
        """Return the record with the given record_id.

        Args:
            record_id: The integer ID to look up.

        Returns:
            The matching ProductionRecord.

        Raises:
            ValueError: If no record with the given ID exists.
        """
        for rec in self._load():
            if rec.record_id == record_id:
                return rec
        raise ValueError(
            f"Kayıt bulunamadı: record_id={record_id}"
        )

    def filter_records(
        self,
        date_from: datetime.date | str | None = None,
        date_to: datetime.date | str | None = None,
        machine_id: str | None = None,
        product_code: str | None = None,
        shift: Shift | str | None = None,
    ) -> list[ProductionRecord]:
        """Filter records by one or more criteria.  Filters combine with AND.

        Date bounds are inclusive.

        Args:
            date_from: Earliest date (inclusive).  ISO str or datetime.date.
            date_to: Latest date (inclusive).  ISO str or datetime.date.
            machine_id: Filter by machine ID.
            product_code: Filter by product code.
            shift: Filter by shift (Shift enum or string value).

        Returns:
            List of matching ProductionRecord instances.
        """
        # Normalise filter values
        d_from: datetime.date | None = None
        d_to: datetime.date | None = None

        if date_from is not None:
            if isinstance(date_from, str):
                d_from = datetime.date.fromisoformat(date_from)
            elif isinstance(date_from, datetime.date):
                d_from = date_from
            else:
                raise TypeError(
                    "date_from datetime.date veya ISO metin olmalıdır."
                )

        if date_to is not None:
            if isinstance(date_to, str):
                d_to = datetime.date.fromisoformat(date_to)
            elif isinstance(date_to, datetime.date):
                d_to = date_to
            else:
                raise TypeError(
                    "date_to datetime.date veya ISO metin olmalıdır."
                )

        shift_filter: Shift | None = None
        if shift is not None:
            if isinstance(shift, Shift):
                shift_filter = shift
            elif isinstance(shift, str):
                shift_filter = Shift(shift.strip().lower())
            else:
                raise TypeError(
                    "shift Shift enum veya metin olmalıdır."
                )

        result: list[ProductionRecord] = []
        for rec in self._load():
            if d_from is not None and rec.production_date < d_from:
                continue
            if d_to is not None and rec.production_date > d_to:
                continue
            if machine_id is not None and rec.machine_id != machine_id:
                continue
            if product_code is not None and rec.product_code != product_code:
                continue
            if shift_filter is not None and rec.shift != shift_filter:
                continue
            result.append(rec)

        return result

    def count(self) -> int:
        """Return the total number of records in the store."""
        return len(self._load())
