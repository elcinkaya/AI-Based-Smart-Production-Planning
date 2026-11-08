"""
loading.py - DataFrame loading and MP3 boundary conversions (plan Section 5).

- load_records_dataframe: reads a record file (.csv or .json, MP3 file rules)
  into the *raw* DataFrame: columns exactly RECORD_COLUMNS, every column of
  the pandas ``"string"`` dtype, empty / whitespace-only values as <NA>.
  The same data loaded from CSV and JSON gives the same DataFrame.
- records_to_dataframe: list of MP3 ProductionRecord -> typed frame with the
  clean_df types of Section 3.2.
- dataframe_to_records: typed frame -> list of MP3 ProductionRecord; every
  row is validated with ``ProductionRecord.from_dict``.

The two record conversions are the only places in the package where a
per-row Python loop is allowed (plan Section 3.1 boundary exception).

Differences from the MP3 ``load_records_*`` functions (by plan decision):
a missing file raises ValueError (MP3 returns an empty list) and the values
are not validated or converted here; validation is the cleaning step.

No print/input; error messages are Turkish.  Inputs are never modified.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import datetime
import json
import os

import pandas as pd

from production_analysis.schema import DATE_COLUMN, RECORD_COLUMNS, TEXT_COLUMNS
from production_records.record import ProductionRecord

#: Supported record file extensions (MP3 rule).
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".csv", ".json")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_path(path) -> str:
    """Return *path* as text after checking type, extension and existence.

    Raises:
        TypeError: If *path* is not a str or os.PathLike.
        ValueError: If the path is empty, the extension is not supported or
            the file does not exist.
    """
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError("Dosya yolu (path) metin (str) olmalıdır.")
    text = os.fspath(path)
    if not str(text).strip():
        raise ValueError("Dosya yolu (path) boş olamaz.")
    extension = os.path.splitext(text)[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Desteklenmeyen dosya uzantısı: '{extension}'. "
            "Yalnızca .csv ve .json dosyaları desteklenir."
        )
    if not os.path.isfile(text):
        raise ValueError(f"Kayıt dosyası bulunamadı: {text}")
    return text


def _empty_raw_frame() -> pd.DataFrame:
    """Return an empty raw frame (RECORD_COLUMNS, all ``"string"`` dtype)."""
    return pd.DataFrame(
        {column: pd.array([], dtype="string") for column in RECORD_COLUMNS},
        columns=RECORD_COLUMNS,
    )


def _blank_to_na(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a new raw frame where empty / whitespace-only texts are <NA>.

    Works column by column with vectorized string methods (no row loop).
    Non-blank values are kept exactly as read (no stripping, no correction).
    """
    result = pd.DataFrame(index=pd.RangeIndex(len(frame)))
    for column in RECORD_COLUMNS:
        values = frame[column].astype("string").reset_index(drop=True)
        blank = values.str.strip().eq("").fillna(False).astype(bool)
        result[column] = values.mask(blank)
    return result


def _read_csv_frame(path: str) -> pd.DataFrame:
    """Read a record CSV file as text; the header must equal RECORD_COLUMNS.

    Raises:
        ValueError: If the header is wrong, a row is malformed or the file is
            not valid UTF-8.
    """
    try:
        frame = pd.read_csv(
            path,
            dtype="string",
            keep_default_na=False,
            na_filter=False,
            encoding="utf-8",
            index_col=False,
            on_bad_lines="error",
        )
    except (pd.errors.ParserError, UnicodeDecodeError) as err:
        raise ValueError(f"'{path}' CSV dosyası okunamadı (bozuk satır veya kodlama): {err}") from err
    except pd.errors.EmptyDataError as err:
        raise ValueError(f"'{path}' CSV dosyasında başlık satırı bulunamadı.") from err

    header = [str(column) for column in frame.columns]
    if header != RECORD_COLUMNS:
        raise ValueError(
            f"'{path}' dosyasında beklenen başlık satırı bulunamadı. "
            f"Beklenen: '{','.join(RECORD_COLUMNS)}', Bulunan: '{','.join(header)}'"
        )
    return frame


def _read_json_frame(path: str) -> pd.DataFrame:
    """Read a record JSON file ``{'schema_version': 1, 'records': [...]}`` as text.

    JSON numbers are converted with ``str`` (same text as the CSV writer),
    JSON null becomes <NA>.  A key missing from a record is treated as null.

    Raises:
        ValueError: If the JSON is invalid, the 'records' key is missing or not
            a list, a record is not an object, or the record keys differ from
            RECORD_COLUMNS.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as err:
        raise ValueError(f"'{path}' dosyası geçersiz JSON içeriyor: {err}") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"'{path}' dosyası UTF-8 olarak okunamadı: {err}") from err

    if not isinstance(data, dict) or "records" not in data:
        raise ValueError(f"'{path}' dosyasında 'records' anahtarı bulunamadı.")
    records = data["records"]
    if not isinstance(records, list):
        raise ValueError(f"'{path}' dosyasındaki 'records' bir liste olmalıdır.")
    if not records:
        return _empty_raw_frame()
    if not all(isinstance(item, dict) for item in records):
        raise ValueError(f"'{path}' dosyasındaki her kayıt bir JSON nesnesi (sözlük) olmalıdır.")

    keys = set().union(*records)
    unknown = sorted(keys - set(RECORD_COLUMNS))
    missing = [column for column in RECORD_COLUMNS if column not in keys]
    if unknown or missing:
        raise ValueError(
            f"'{path}' dosyasındaki kayıt alanları beklenen sütunlarla uyuşmuyor. "
            f"Eksik: {missing or '-'}, Beklenmeyen: {unknown or '-'}"
        )

    # dtype=object keeps the Python values (ints stay ints, None stays None),
    # then astype("string") converts every value with str() and None -> <NA>.
    frame = pd.DataFrame(records, columns=RECORD_COLUMNS, dtype=object)
    return frame.astype("string")


def _require_columns(df: pd.DataFrame, columns: list) -> None:
    """Raise ValueError if a required column is missing from *df*."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"DataFrame'de gerekli sütun(lar) eksik: {', '.join(missing)}")


def _to_python(value):
    """Return a plain Python value for a DataFrame cell; missing -> None."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if hasattr(value, "item") and not isinstance(value, (str, datetime.date)):
        return value.item()  # NumPy scalar -> Python scalar
    return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_records_dataframe(path: str) -> pd.DataFrame:
    """Load a record file into the raw string DataFrame.

    The format is chosen by the extension: ``.csv`` (UTF-8, header row equal
    to RECORD_COLUMNS) or ``.json`` (``{'schema_version': 1, 'records': [...]}``).
    A 0-byte file returns an empty frame.

    Returns columns (all pandas ``"string"`` dtype, missing value <NA>):
        record_id, production_date, shift, machine_id, product_code,
        planned_units, actual_units, downtime_hours.
    Empty and whitespace-only values are <NA>; all other values are kept as
    the exact text of the file (invalid values such as 'abc' are preserved).
    Index is 0..n-1 in file order.

    Args:
        path: Path of the .csv or .json file.

    Returns:
        New raw DataFrame.

    Raises:
        TypeError: If *path* is not a str / os.PathLike.
        ValueError: If the extension is not supported, the file does not
            exist, the CSV header / JSON structure is wrong or the file is
            corrupt.
    """
    source = _validate_path(path)
    if os.path.getsize(source) == 0:
        return _empty_raw_frame()
    if source.lower().endswith(".csv"):
        frame = _read_csv_frame(source)
    else:
        frame = _read_json_frame(source)
    return _blank_to_na(frame)


def records_to_dataframe(records: list) -> pd.DataFrame:
    """Convert MP3 ProductionRecord objects into a typed DataFrame.

    Returns columns RECORD_COLUMNS with the clean_df types of Section 3.2:
        record_id (int64), production_date (datetime64), shift (string),
        machine_id (string), product_code (string), planned_units (int64),
        actual_units (int64), downtime_hours (float64).
    Row order equals the list order; index 0..n-1.  An empty list gives an
    empty typed frame.  (Boundary conversion: a per-record loop is allowed.)

    Args:
        records: List of ProductionRecord objects with assigned record_id.

    Returns:
        New typed DataFrame.

    Raises:
        TypeError: If *records* is not a list or an item is not a
            ProductionRecord.
        ValueError: If a record has no record_id (None).
    """
    if not isinstance(records, list):
        raise TypeError("records bir liste (list) olmalıdır.")
    for position, record in enumerate(records):
        if not isinstance(record, ProductionRecord):
            raise TypeError(f"Kayıt listesinin {position}. elemanı ProductionRecord türünde olmalıdır.")
        if record.record_id is None:
            raise ValueError(
                f"Kayıt listesinin {position}. elemanının record_id değeri atanmamış (None)."
            )

    rows = [record.to_dict() for record in records]
    columns = {column: [row[column] for row in rows] for column in RECORD_COLUMNS}

    frame = pd.DataFrame(
        {
            "record_id": pd.array(columns["record_id"], dtype="int64"),
            DATE_COLUMN: pd.to_datetime(
                pd.Series(columns[DATE_COLUMN], dtype="string"), format="%Y-%m-%d"
            ),
            **{column: pd.array(columns[column], dtype="string") for column in TEXT_COLUMNS},
            "planned_units": pd.array(columns["planned_units"], dtype="int64"),
            "actual_units": pd.array(columns["actual_units"], dtype="int64"),
            "downtime_hours": pd.array(columns["downtime_hours"], dtype="float64"),
        },
        columns=RECORD_COLUMNS,
    )
    return frame


def dataframe_to_records(df: pd.DataFrame) -> list:
    """Convert a typed DataFrame into MP3 ProductionRecord objects.

    Expected columns (extra columns are ignored):
        record_id (int64), production_date (datetime64 or ISO text),
        shift / machine_id / product_code (text), planned_units (int64),
        actual_units (int64), downtime_hours (float64).
    Every row is validated by ``ProductionRecord.from_dict`` (MP3 rules);
    integer columns must hold integer values (float columns are rejected by
    MP3, nothing is silently converted).  (Boundary conversion: a per-row
    loop is allowed.)

    Args:
        df: Typed record DataFrame (e.g. clean_df).

    Returns:
        List of ProductionRecord objects in row order.

    Raises:
        TypeError: If *df* is not a DataFrame.
        ValueError: If a column is missing or a row fails MP3 validation.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df bir pandas DataFrame olmalıdır.")
    _require_columns(df, RECORD_COLUMNS)

    column_values = {column: df[column].tolist() for column in RECORD_COLUMNS}
    records = []
    for position in range(len(df)):
        data = {column: _to_python(column_values[column][position]) for column in RECORD_COLUMNS}
        try:
            records.append(ProductionRecord.from_dict(data))
        except (TypeError, ValueError) as err:
            raise ValueError(
                f"{position}. satır (record_id={data['record_id']}) MP3 doğrulamasından geçemedi: {err}"
            ) from err
    return records


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "load_records_dataframe",
    "records_to_dataframe",
    "dataframe_to_records",
]
