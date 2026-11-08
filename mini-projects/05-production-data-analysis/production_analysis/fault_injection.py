"""
fault_injection.py - Controlled fault injection into the raw record set.

Implements the injection rules of plan Section 5 (Kişi A, stage 4):

1. ``rng = np.random.default_rng(seed)`` - the only randomness of Mini
   Project 5 (draw order below is part of the reproducibility contract).
2. ``picked = rng.choice(len(clean_df), size=66, replace=False)``; the picked
   row positions are split into consecutive slices in FAULT_PLAN order
   (first 12 -> missing_actual_units, next 12 -> missing_downtime_hours, ...).
   Exactly one fault is applied to each picked row.
3. ``remaining = np.setdiff1d(np.arange(len(clean_df)), picked)``;
   ``duplicated = rng.choice(remaining, size=10, replace=False)``.  Copies of
   these rows are appended with new record_ids (max record_id + 1 ...,
   i.e. 601-610 for the 600-row set); the key stays the same.
4. The fault log has one row per picked row (in slice order) followed by one
   ``duplicate_key`` row per copy (new record_id): 66 + 10 = 76 rows.

Fault values: missing -> <NA>; negative_actual_units -> -(actual_units + 1);
non_numeric_actual_units -> 'abc'; downtime_too_high -> '9.5';
invalid_shift -> 'evening'; unknown_machine_id -> 'M9';
invalid_date -> '2026-13-40'; zero_planned_units -> '0'.

save_dirty_records writes the dirty frame as CSV (MP3 CSV layout, missing
values as empty fields) and as JSON (``{'schema_version': 1, 'records': [...]}``;
valid numbers as JSON numbers, corrupt values as text, missing values as null).

Inputs are never modified.  No print/input; error messages are Turkish.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from production_analysis.schema import (
    DATE_COLUMN,
    FAULT_LOG_COLUMNS,
    FLOAT_COLUMNS,
    INT_COLUMNS,
    JSON_SCHEMA_VERSION,
    RECORD_COLUMNS,
)

# ---------------------------------------------------------------------------
# Constants (plan Section 5)
# ---------------------------------------------------------------------------

#: (fault_type, row count) in slice order.
FAULT_PLAN: list[tuple[str, int]] = [
    ("missing_actual_units", 12),
    ("missing_downtime_hours", 12),
    ("negative_actual_units", 6),
    ("non_numeric_actual_units", 6),
    ("downtime_too_high", 6),
    ("invalid_shift", 6),
    ("unknown_machine_id", 6),
    ("invalid_date", 6),
    ("zero_planned_units", 6),
]

#: Number of duplicated rows appended at the end.
DUPLICATE_COUNT: int = 10

#: Fault type written to the log for the appended copies.
DUPLICATE_FAULT_TYPE: str = "duplicate_key"

#: Default seed (same as MP4 DEFAULT_SEED).
DEFAULT_FAULT_SEED: int = 42

#: Total number of corrupted rows (sum of FAULT_PLAN counts = 66).
CORRUPTED_ROW_COUNT: int = sum(count for _, count in FAULT_PLAN)

#: fault_type -> (column, replacement text or None for <NA>).
#: negative_actual_units is computed from the original value (see below).
_CONSTANT_FAULTS: dict[str, tuple[str, str | None]] = {
    "missing_actual_units": ("actual_units", None),
    "missing_downtime_hours": ("downtime_hours", None),
    "non_numeric_actual_units": ("actual_units", "abc"),
    "downtime_too_high": ("downtime_hours", "9.5"),
    "invalid_shift": ("shift", "evening"),
    "unknown_machine_id": ("machine_id", "M9"),
    "invalid_date": (DATE_COLUMN, "2026-13-40"),
    "zero_planned_units": ("planned_units", "0"),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_frame(df, name: str) -> pd.DataFrame:
    """Check that *df* is a DataFrame holding all RECORD_COLUMNS.

    Raises:
        TypeError: If *df* is not a DataFrame.
        ValueError: If a required column is missing.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} bir pandas DataFrame olmalıdır.")
    missing = [column for column in RECORD_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{name} içinde gerekli sütun(lar) eksik: {', '.join(missing)}")
    return df


def _validate_seed(seed) -> int:
    """Validate the random seed (int >= 0, bool rejected).

    Raises:
        TypeError: If *seed* is not an integer.
        ValueError: If *seed* is negative.
    """
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed tam sayı (int) olmalıdır.")
    if seed < 0:
        raise ValueError("seed 0 veya daha büyük olmalıdır.")
    return int(seed)


def _as_raw_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Return a new frame with RECORD_COLUMNS as pandas ``"string"`` columns.

    String columns are copied unchanged; datetime columns are written as ISO
    text (YYYY-MM-DD); other columns are converted with ``astype("string")``
    (int64 800 -> '800', float64 0.5 -> '0.5', same text as the MP3 CSV writer).
    The index is reset to 0..n-1.  The input is not modified.
    """
    result = pd.DataFrame(index=pd.RangeIndex(len(df)))
    for column in RECORD_COLUMNS:
        values = df[column].reset_index(drop=True)
        if pd.api.types.is_datetime64_any_dtype(values):
            values = values.dt.strftime("%Y-%m-%d")
        result[column] = values.astype("string")
    return result


def _numeric_record_ids(raw: pd.DataFrame) -> pd.Series:
    """Return record_id as int64; raise ValueError if an id is not an integer."""
    ids = pd.to_numeric(raw["record_id"], errors="coerce")
    if ids.isna().any() or not (ids == ids.round()).all():
        raise ValueError("Hata enjeksiyonu için tüm record_id değerleri tam sayı olmalıdır.")
    return ids.astype("int64")


def _negative_actual_units(values: pd.Series) -> pd.Series:
    """Return -(actual_units + 1) as text for the given original values.

    Raises:
        ValueError: If an original actual_units value is not an integer.
    """
    numbers = pd.to_numeric(values, errors="coerce")
    if numbers.isna().any() or not (numbers == numbers.round()).all():
        raise ValueError("negative_actual_units için seçilen satırlarda actual_units tam sayı olmalıdır.")
    return (-(numbers.astype("int64") + 1)).astype("string")


def _json_column(text: pd.Series, column: str) -> pd.Series:
    """Return the JSON-ready object column for one raw text column.

    - missing (<NA>) -> None (JSON null)
    - INT_COLUMNS: integer text -> Python int
    - FLOAT_COLUMNS: finite number text -> Python float
    - everything else -> the original text
    A number is used only if writing it back gives exactly the same text,
    so the CSV and JSON files load into the same raw DataFrame.
    """
    present = text.notna()
    values = text.astype(object).where(present, None)

    if column in INT_COLUMNS or column in FLOAT_COLUMNS:
        numbers = pd.to_numeric(text, errors="coerce")
        target = "Int64" if column in INT_COLUMNS else "Float64"
        if column in INT_COLUMNS:
            numbers = numbers.where(numbers == numbers.round())
        else:
            numbers = numbers.where(np.isfinite(numbers.astype("float64")))
        typed = numbers.astype(target)
        same_text = typed.astype("string").eq(text).fillna(False).astype(bool)
        use_number = present & typed.notna().fillna(False).astype(bool) & same_text
        values = values.where(~use_number, typed.astype(object))
    return values


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_faults(clean_df: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject the FAULT_PLAN faults and DUPLICATE_COUNT duplicates.

    Args:
        clean_df: Raw record frame without faults (normally
            ``load_records_dataframe('raw_records_clean.csv')``): columns
            RECORD_COLUMNS, preferably all pandas ``"string"`` dtype.  Typed
            frames are accepted and converted to text first.  Row positions
            (0..n-1 after ``reset_index``) are used for the random draws.
        seed: Seed of ``np.random.default_rng`` (default 42).

    Returns:
        ``(dirty_df, fault_log_df)``:
        - dirty_df: RECORD_COLUMNS, all ``"string"`` dtype, missing <NA>;
          ``len(clean_df) + 10`` rows (610 for the 600-row set), index 0..n-1.
        - fault_log_df: record_id (int64), fault_type (string); 66 corrupted
          rows in slice order followed by 10 duplicate_key rows (76 rows).

    Raises:
        TypeError: If *clean_df* is not a DataFrame or *seed* is not an int.
        ValueError: If a column is missing, the frame has fewer than 76 rows,
            a record_id is not an integer or *seed* is negative.
    """
    _validate_frame(clean_df, "clean_df")
    rng_seed = _validate_seed(seed)
    row_count = len(clean_df)
    needed = CORRUPTED_ROW_COUNT + DUPLICATE_COUNT
    if row_count < needed:
        raise ValueError(
            f"Hata enjeksiyonu için en az {needed} satır gereklidir (verilen: {row_count})."
        )

    raw = _as_raw_strings(clean_df)
    record_ids = _numeric_record_ids(raw)
    dirty = raw.copy()

    # Draw order is fixed by the plan: picked first, then duplicated.
    rng = np.random.default_rng(rng_seed)
    picked = rng.choice(row_count, size=CORRUPTED_ROW_COUNT, replace=False)
    fault_types = np.repeat(
        np.array([fault for fault, _ in FAULT_PLAN]),
        [count for _, count in FAULT_PLAN],
    )

    # One vectorized assignment per fault type (9 iterations, no row loop).
    for fault_type, _ in FAULT_PLAN:
        rows = picked[fault_types == fault_type]
        if fault_type == "negative_actual_units":
            dirty.loc[rows, "actual_units"] = _negative_actual_units(raw.loc[rows, "actual_units"])
        else:
            column, value = _CONSTANT_FAULTS[fault_type]
            dirty.loc[rows, column] = pd.NA if value is None else value

    remaining = np.setdiff1d(np.arange(row_count), picked)
    duplicated = rng.choice(remaining, size=DUPLICATE_COUNT, replace=False)
    new_ids = int(record_ids.max()) + 1 + np.arange(DUPLICATE_COUNT, dtype=np.int64)

    copies = raw.iloc[duplicated].reset_index(drop=True)
    copies["record_id"] = pd.array(new_ids.astype(str), dtype="string")
    dirty_df = pd.concat([dirty, copies], ignore_index=True)

    fault_log_df = pd.DataFrame(
        {
            "record_id": np.concatenate([record_ids.to_numpy()[picked], new_ids]).astype(np.int64),
            "fault_type": pd.array(
                np.concatenate([fault_types, np.repeat(DUPLICATE_FAULT_TYPE, DUPLICATE_COUNT)]),
                dtype="string",
            ),
        },
        columns=FAULT_LOG_COLUMNS,
    )
    return dirty_df, fault_log_df


def save_dirty_records(dirty_df: pd.DataFrame, csv_path: str, json_path: str) -> None:
    """Write the dirty record frame to a CSV and a JSON file.

    CSV: UTF-8, header row RECORD_COLUMNS, values as text, missing values as
    empty fields (MP3 CSV layout).  JSON: ``{'schema_version': 1, 'records':
    [...]}`` where valid numbers are JSON numbers, corrupt values text and
    missing values null.  Both files load into the same raw DataFrame with
    ``load_records_dataframe``.  Parent folders are created.

    Args:
        dirty_df: Raw record frame (RECORD_COLUMNS; normally ``inject_faults``
            output).
        csv_path: Target .csv path.
        json_path: Target .json path.

    Raises:
        TypeError: If *dirty_df* is not a DataFrame or a path is not a str.
        ValueError: If a column is missing or a path has the wrong extension.
    """
    _validate_frame(dirty_df, "dirty_df")
    targets = {}
    for label, path, extension in (("csv_path", csv_path, ".csv"), ("json_path", json_path, ".json")):
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError(f"{label} metin (str) olmalıdır.")
        text = os.fspath(path)
        if os.path.splitext(text)[1].lower() != extension:
            raise ValueError(f"{label} '{extension}' uzantılı olmalıdır: {text}")
        parent = os.path.dirname(os.path.abspath(text))
        os.makedirs(parent, exist_ok=True)
        targets[label] = text

    raw = _as_raw_strings(dirty_df)
    raw.to_csv(targets["csv_path"], index=False, encoding="utf-8", lineterminator="\r\n")

    json_frame = pd.DataFrame(
        {column: _json_column(raw[column], column) for column in RECORD_COLUMNS},
        columns=RECORD_COLUMNS,
    )
    payload = {
        "schema_version": JSON_SCHEMA_VERSION,
        "records": json_frame.to_dict(orient="records"),
    }
    tmp_path = targets["json_path"] + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        # allow_nan=False guarantees that no NaN leaks into the JSON file.
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    os.replace(tmp_path, targets["json_path"])


__all__ = [
    "FAULT_PLAN",
    "DUPLICATE_COUNT",
    "DUPLICATE_FAULT_TYPE",
    "DEFAULT_FAULT_SEED",
    "CORRUPTED_ROW_COUNT",
    "inject_faults",
    "save_dirty_records",
]
