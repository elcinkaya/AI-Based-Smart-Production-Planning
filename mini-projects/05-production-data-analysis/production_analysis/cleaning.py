"""
cleaning.py - Detection and cleaning of faulty production records (plan 3.3).

- clean_records: raw string frame -> (clean_df, cleaning_log_df).  The rules,
  the issue codes and the processing order are exactly those of Section 3.3:

  1. empty / whitespace-only texts are treated as missing (<NA>);
  2. type conversion with ``errors='coerce'`` and issue flagging
     (one boolean mask per issue code);
  3. rows with at least one ``dropped`` issue are removed;
  4. missing ``downtime_hours`` of the remaining rows is filled with 0.0
     (the only documented correction, MP3 default value);
  5. among the remaining rows, repeated (production_date, shift, machine_id)
     keys are removed, keeping the smallest record_id (``duplicate_key``).

- summarize_cleaning: counts of the cleaning step for the report.

Rules of this module:
- Validation is vectorized: boolean masks built with ``pd.to_datetime``,
  ``pd.to_numeric``, ``isin`` and ``duplicated``.  No row-by-row DataFrame
  iteration, no row-wise apply and no per-row Python loop (the only loops
  run over the fixed list of columns / issue codes).
- No new rule is added and no rule is relaxed; nothing is silently corrected.
- Input frames are never modified; new frames are returned.
- No print/input; error messages are Turkish.

Author: Kişi B
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from production_analysis.schema import (
    CLEANING_LOG_COLUMNS,
    DATE_COLUMN,
    ISSUE_ACTIONS,
    ISSUE_CODES,
    KEY_FIELDS,
    RECORD_COLUMNS,
    SHIFT_HOURS,
    TEXT_COLUMNS,
    VALID_SHIFTS,
)

#: Strict ISO calendar date text (YYYY-MM-DD), same rule as MP3 ``_validate_date``.
#: ``pd.to_datetime(..., format='%Y-%m-%d')`` alone also accepts e.g. '2026-1-5'.
_ISO_DATE_PATTERN: str = r"\d{4}-\d{2}-\d{2}"

#: (production_date, shift, machine_id) uniqueness key (MP3 ``get_key``).
_DUPLICATE_KEY: list[str] = [DATE_COLUMN, "shift", "machine_id"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_frame(df, name: str) -> None:
    """Raise TypeError if *df* is not a pandas DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} bir pandas DataFrame olmalıdır.")


def _require_columns(df: pd.DataFrame, columns: list, name: str) -> None:
    """Raise ValueError if a required column is missing from *df*."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{name} içinde gerekli sütun(lar) eksik: {', '.join(missing)}")


def _empty_clean_frame() -> pd.DataFrame:
    """Return an empty clean_df with the Section 3.2 column order and types."""
    return pd.DataFrame(
        {
            "record_id": pd.Series([], dtype="int64"),
            DATE_COLUMN: pd.Series([], dtype="datetime64[us]"),
            **{column: pd.Series([], dtype="string") for column in TEXT_COLUMNS},
            "planned_units": pd.Series([], dtype="int64"),
            "actual_units": pd.Series([], dtype="int64"),
            "downtime_hours": pd.Series([], dtype="float64"),
        },
        columns=RECORD_COLUMNS,
    )


def _empty_log_frame() -> pd.DataFrame:
    """Return an empty cleaning_log_df (record_id int64, issue/action string)."""
    return pd.DataFrame(
        {
            "record_id": pd.Series([], dtype="int64"),
            "issue": pd.Series([], dtype="string"),
            "action": pd.Series([], dtype="string"),
        },
        columns=CLEANING_LOG_COLUMNS,
    )


def _normalize_raw(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Step 1: new string frame of RECORD_COLUMNS; blank texts become <NA>.

    Non-blank values are kept exactly as given (no stripping, no correction).
    """
    result = pd.DataFrame(index=pd.RangeIndex(len(raw_df)))
    for column in RECORD_COLUMNS:  # fixed list of 8 columns, not a row loop
        values = raw_df[column].astype("string").reset_index(drop=True)
        blank = values.str.strip().eq("").fillna(False).astype(bool)
        result[column] = values.mask(blank)
    return result


def _to_float(values: pd.Series) -> pd.Series:
    """Return a float64 Series; non-numeric texts and <NA> become NaN."""
    numbers = pd.to_numeric(values, errors="coerce")
    return pd.Series(
        numbers.to_numpy(dtype="float64", na_value=np.nan), index=values.index
    )


def _parse_record_ids(record_id: pd.Series) -> pd.Series:
    """Return record_id as int64 after checking it is a usable identifier.

    record_id is assigned by the MP3 RecordStore and is the key of the
    cleaning log; it is not a cleaning field of Section 3.3.  A missing,
    non-integer, < 1 or repeated record_id therefore breaks the input
    contract and raises ValueError instead of being "cleaned".
    """
    numbers = _to_float(record_id)
    bad = numbers.isna() | (numbers < 1) | (numbers != np.floor(numbers))
    if bad.any():
        examples = ", ".join(record_id[bad].astype("string").fillna("<NA>").head(5).tolist())
        raise ValueError(
            "record_id sütunu eksik veya geçersiz değer içeriyor "
            f"(1 veya daha büyük tam sayı olmalı): {examples}"
        )
    ids = numbers.astype("int64")
    repeated = ids.duplicated(keep=False)
    if repeated.any():
        examples = ", ".join(str(value) for value in ids[repeated].unique()[:5])
        raise ValueError(f"record_id değerleri benzersiz olmalıdır; tekrar eden: {examples}")
    return ids


def _build_log(record_ids: pd.Series, issue_masks: dict) -> pd.DataFrame:
    """Build cleaning_log_df: one row per (record, issue), sorted by record_id.

    Within a record the issues follow the Section 3.3 table order.
    """
    parts = [
        pd.DataFrame({"record_id": record_ids[mask].to_numpy(), "issue": issue})
        for issue, mask in issue_masks.items()  # loop over issue codes only
        if mask.any()
    ]
    if not parts:
        return _empty_log_frame()
    log = pd.concat(parts, ignore_index=True)
    log["issue_order"] = log["issue"].map({code: i for i, code in enumerate(ISSUE_CODES)})
    log = log.sort_values(["record_id", "issue_order"], kind="stable").reset_index(drop=True)
    return pd.DataFrame(
        {
            "record_id": log["record_id"].astype("int64"),
            "issue": log["issue"].astype("string"),
            "action": log["issue"].map(ISSUE_ACTIONS).astype("string"),
        },
        columns=CLEANING_LOG_COLUMNS,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_records(
    raw_df: pd.DataFrame,
    machine_master: pd.DataFrame,
    product_master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detect and clean faulty records with the Section 3.3 rules and order.

    Input ``raw_df`` (``load_records_dataframe`` output): columns
    RECORD_COLUMNS, text values (pandas ``"string"`` dtype), missing <NA>.
    Extra columns are ignored.  ``machine_master`` must contain
    ``machine_id`` and ``product_master`` must contain ``product_code``
    (``build_machine_master`` / ``build_product_master`` outputs).

    Returned ``clean_df`` columns (RECORD_COLUMNS order) and dtypes:
        record_id (int64, unique, ascending), production_date (datetime64),
        shift (string: morning/afternoon/night), machine_id (string, in the
        machine master), product_code (string, in the product master),
        planned_units (int64, > 0), actual_units (int64, >= 0),
        downtime_hours (float64, 0 <= x <= 8).
    Rows are sorted by record_id and the index is 0..n-1.

    Returned ``cleaning_log_df`` columns: record_id (int64), issue (string,
    an ISSUE_ACTIONS key), action (string, ``ISSUE_ACTIONS[issue]``:
    'dropped' or 'filled').  Every issue of a row is a separate log row;
    the log is sorted by record_id, then by the Section 3.3 issue order.

    Issue rules (each value is checked only when it is present, so a value
    is either missing or invalid, never both):
        missing_key_field: a KEY_FIELDS value is missing -> dropped
        missing_actual_units: actual_units missing -> dropped
        missing_downtime_hours: downtime_hours missing -> filled (0.0)
        invalid_date: not ISO YYYY-MM-DD or not a calendar date -> dropped
        invalid_shift: not in VALID_SHIFTS -> dropped
        unknown_machine_id / unknown_product_code: not in master -> dropped
        invalid_planned_units: not a number, <= 0 or not integer-valued
        invalid_actual_units: not a number, < 0 or not integer-valued
        invalid_downtime_hours: not a number, < 0 or > SHIFT_HOURS (8)
        duplicate_key: same (date, shift, machine) as a remaining row with a
            smaller record_id -> dropped

    The fill of step 4 is applied only to the rows kept in step 3; a
    ``missing_downtime_hours`` issue of a dropped row is still logged
    (every issue is logged), but that row is not part of clean_df.

    Args:
        raw_df: Raw record frame.
        machine_master: Machine master table.
        product_master: Product master table.

    Returns:
        (clean_df, cleaning_log_df) as new DataFrames.

    Raises:
        TypeError: If an argument is not a DataFrame.
        ValueError: If a required column is missing, or record_id is
            missing, not a positive integer or not unique.
    """
    _require_frame(raw_df, "raw_df")
    _require_frame(machine_master, "machine_master")
    _require_frame(product_master, "product_master")
    _require_columns(raw_df, RECORD_COLUMNS, "raw_df")
    _require_columns(machine_master, ["machine_id"], "machine_master")
    _require_columns(product_master, ["product_code"], "product_master")

    if raw_df.empty:
        return _empty_clean_frame(), _empty_log_frame()

    # (1) blank / whitespace-only -> <NA>
    raw = _normalize_raw(raw_df)
    record_ids = _parse_record_ids(raw["record_id"])

    # (2) type conversion (errors='coerce') and issue flagging
    missing = raw.isna()
    dates = pd.to_datetime(raw[DATE_COLUMN], format="%Y-%m-%d", errors="coerce")
    iso_text = raw[DATE_COLUMN].str.fullmatch(_ISO_DATE_PATTERN).fillna(False).astype(bool)
    planned = _to_float(raw["planned_units"])
    actual = _to_float(raw["actual_units"])
    downtime = _to_float(raw["downtime_hours"])

    known_machines = machine_master["machine_id"].astype("string").dropna().unique()
    known_products = product_master["product_code"].astype("string").dropna().unique()

    present_date = ~missing[DATE_COLUMN]
    present_shift = ~missing["shift"]
    present_machine = ~missing["machine_id"]
    present_product = ~missing["product_code"]
    present_planned = ~missing["planned_units"]
    present_actual = ~missing["actual_units"]
    present_downtime = ~missing["downtime_hours"]

    # NaN comparisons are False, so "not (valid condition)" also flags texts
    # that could not be converted.
    planned_ok = (planned > 0) & (planned == np.floor(planned))
    actual_ok = (actual >= 0) & (actual == np.floor(actual))
    downtime_ok = (downtime >= 0) & (downtime <= SHIFT_HOURS)

    issue_masks = {
        "missing_key_field": missing[KEY_FIELDS].any(axis=1),
        "missing_actual_units": missing["actual_units"],
        "missing_downtime_hours": missing["downtime_hours"],
        "invalid_date": present_date & (dates.isna() | ~iso_text),
        "invalid_shift": present_shift & ~raw["shift"].isin(VALID_SHIFTS).fillna(False).astype(bool),
        "unknown_machine_id": present_machine
        & ~raw["machine_id"].isin(known_machines).fillna(False).astype(bool),
        "unknown_product_code": present_product
        & ~raw["product_code"].isin(known_products).fillna(False).astype(bool),
        "invalid_planned_units": present_planned & ~planned_ok,
        "invalid_actual_units": present_actual & ~actual_ok,
        "invalid_downtime_hours": present_downtime & ~downtime_ok,
    }
    issue_masks = {issue: mask.astype(bool) for issue, mask in issue_masks.items()}

    # (3) remove rows that have at least one 'dropped' issue
    drop_mask = pd.Series(False, index=raw.index)
    for issue, mask in issue_masks.items():  # loop over issue codes only
        if ISSUE_ACTIONS[issue] == "dropped":
            drop_mask = drop_mask | mask
    keep = ~drop_mask

    typed = pd.DataFrame(
        {
            "record_id": record_ids,
            DATE_COLUMN: dates,
            **{column: raw[column] for column in TEXT_COLUMNS},
            "planned_units": planned,
            "actual_units": actual,
            "downtime_hours": downtime,
        },
        columns=RECORD_COLUMNS,
    )
    kept = typed.loc[keep].copy()

    # (4) fill missing downtime_hours of the remaining rows with 0.0
    kept["downtime_hours"] = kept["downtime_hours"].fillna(0.0)

    # (5) duplicate keys among the remaining rows: keep the smallest record_id
    kept = kept.sort_values("record_id", kind="stable")
    duplicate_rows = kept.duplicated(subset=_DUPLICATE_KEY, keep="first")
    duplicate_index = duplicate_rows.index[duplicate_rows.to_numpy()]
    issue_masks["duplicate_key"] = pd.Series(raw.index.isin(duplicate_index), index=raw.index)
    kept = kept.loc[~duplicate_rows]

    clean_df = pd.DataFrame(
        {
            "record_id": kept["record_id"].astype("int64"),
            DATE_COLUMN: kept[DATE_COLUMN],
            **{column: kept[column].astype("string") for column in TEXT_COLUMNS},
            "planned_units": kept["planned_units"].astype("int64"),
            "actual_units": kept["actual_units"].astype("int64"),
            "downtime_hours": kept["downtime_hours"].astype("float64"),
        },
        columns=RECORD_COLUMNS,
    ).reset_index(drop=True)

    cleaning_log_df = _build_log(record_ids, issue_masks)
    return clean_df, cleaning_log_df


def summarize_cleaning(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    cleaning_log_df: pd.DataFrame,
) -> dict:
    """Summarize the result of ``clean_records``.

    Args:
        raw_df: Raw frame given to ``clean_records``.
        clean_df: Clean frame returned by ``clean_records`` (needs record_id).
        cleaning_log_df: Log returned by ``clean_records`` (record_id, issue,
            action).

    Returns:
        Dict with the keys:
            raw_row_count (int): rows of raw_df;
            clean_row_count (int): rows of clean_df;
            dropped_row_count (int): distinct record_ids with a 'dropped'
                issue (a row with several issues is counted once);
            filled_row_count (int): distinct record_ids of clean_df whose
                downtime_hours was filled;
            issue_counts (dict[str, int]): issue -> number of log rows, only
                issues that occur, in the Section 3.3 table order.

    Raises:
        TypeError: If an argument is not a DataFrame.
        ValueError: If a required column is missing.
    """
    _require_frame(raw_df, "raw_df")
    _require_frame(clean_df, "clean_df")
    _require_frame(cleaning_log_df, "cleaning_log_df")
    _require_columns(clean_df, ["record_id"], "clean_df")
    _require_columns(cleaning_log_df, CLEANING_LOG_COLUMNS, "cleaning_log_df")

    action = cleaning_log_df["action"].astype("string")
    dropped_ids = cleaning_log_df.loc[action.eq("dropped").fillna(False).astype(bool), "record_id"]
    filled_ids = cleaning_log_df.loc[action.eq("filled").fillna(False).astype(bool), "record_id"]
    filled_kept = filled_ids[filled_ids.isin(clean_df["record_id"])]

    counts = cleaning_log_df["issue"].astype("string").value_counts()
    issue_counts = {issue: int(counts[issue]) for issue in ISSUE_CODES if issue in counts.index}

    return {
        "raw_row_count": int(len(raw_df)),
        "clean_row_count": int(len(clean_df)),
        "dropped_row_count": int(dropped_ids.nunique()),
        "filled_row_count": int(filled_kept.nunique()),
        "issue_counts": issue_counts,
    }


__all__ = ["clean_records", "summarize_cleaning"]
