"""
report.py - Turkish analysis report and analysis file export (plan Section 5).

- build_analysis_report: report text (data quality, MP3 general block, KPI
  tables, business question answers); nothing is printed.
- print_analysis_report: prints the text built by build_analysis_report.
- save_analysis_outputs: writes the analysis CSV files of Section 4.

Report layout follows the MP3/MP4 framed style (``====`` lines).  The general
result block is produced unchanged by MP3 ``build_summary_report`` (with the
machine group lines); the other sections are added around it.  Rounding
happens only here (2 decimals for percentages, hours as given by the format).

CSV rules: UTF-8, header row, ISO dates (YYYY-MM-DD), no rounding.
``clean_records.csv`` is written by MP3 ``save_records_csv`` after the
``dataframe_to_records`` boundary conversion, so it is byte-compatible with
the MP3 CSV format and readable by MP3 ``RecordStore``.

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import os

import pandas as pd

from production_analysis.kpi import KPI_TABLE_GROUPS, kpi_table_to_group_summaries
from production_analysis.loading import dataframe_to_records
from production_analysis.schema import ISSUE_ACTIONS, ISSUE_CODES, KPI_COLUMNS
from production_records.report import build_summary_report
from production_records.storage import save_records_csv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPORT_TITLE: str = "ÜRETİM VERİSİ ANALİZ RAPORU (PANDAS)"
REPORT_WIDTH: int = 100
SEPARATOR_THICK: str = "=" * REPORT_WIDTH
SEPARATOR_THIN: str = "-" * REPORT_WIDTH
LABEL_WIDTH: int = 26

#: Output file names of save_analysis_outputs (Section 4), in write order.
CLEAN_RECORDS_FILENAME: str = "clean_records.csv"
CLEANING_LOG_FILENAME: str = "cleaning_log.csv"
ANALYSIS_DATASET_FILENAME: str = "analysis_dataset.csv"
KPI_FILENAME_TEMPLATE: str = "kpi_by_{key}.csv"
DAILY_SERIES_FILENAME: str = "daily_series.csv"
WEEKLY_SUMMARY_FILENAME: str = "weekly_summary.csv"

#: Required keys of the inputs of build_analysis_report.
CLEANING_SUMMARY_KEYS: tuple[str, ...] = (
    "raw_row_count",
    "clean_row_count",
    "dropped_row_count",
    "filled_row_count",
    "issue_counts",
)
REPORT_TABLE_KEYS: tuple[str, ...] = ("machine", "product", "shift")
QUESTION_KEYS: tuple[str, ...] = ("q1", "q2", "q3", "q4", "q5", "q6", "q7")

#: Turkish descriptions of the cleaning issue codes.
ISSUE_LABELS: dict[str, str] = {
    "missing_key_field": "Anahtar alan eksik",
    "missing_actual_units": "Gerçekleşen üretim eksik",
    "missing_downtime_hours": "Duruş süresi eksik",
    "invalid_date": "Geçersiz tarih",
    "invalid_shift": "Geçersiz vardiya",
    "unknown_machine_id": "Bilinmeyen makine",
    "unknown_product_code": "Bilinmeyen ürün",
    "invalid_planned_units": "Geçersiz planlanan üretim",
    "invalid_actual_units": "Geçersiz gerçekleşen üretim",
    "invalid_downtime_hours": "Geçersiz duruş süresi",
    "duplicate_key": "Tekrarlanan kayıt anahtarı",
}
ACTION_LABELS: dict[str, str] = {"dropped": "silindi", "filled": "0,0 ile dolduruldu"}

#: Turkish titles of the KPI tables.
TABLE_TITLES: dict[str, str] = {
    "machine": "Makine Bazında",
    "product": "Ürün Bazında",
    "shift": "Vardiya Bazında",
    "day": "Gün Bazında",
    "week": "Hafta Bazında",
}

_TABLE_HEADER: str = (
    f"  {'Grup':<12}{'Kayıt':>6}{'Planlanan':>11}{'Gerçekleşen':>13}{'Fark':>9}"
    f"{'Gerç.%':>8}{'Duruş(sa)':>11}{'Kull.%':>8}{'Kap.%':>8}{'Duruşlu':>9}{'Std':>7}"
)


# ---------------------------------------------------------------------------
# Internal helpers - validation
# ---------------------------------------------------------------------------

def _require_dict(value, name: str, keys: tuple) -> None:
    """Raise TypeError / ValueError if *value* is not a dict with *keys*."""
    if not isinstance(value, dict):
        raise TypeError(f"{name} bir sözlük (dict) olmalıdır.")
    missing = [key for key in keys if key not in value]
    if missing:
        raise ValueError(f"{name} içinde eksik anahtar(lar): {', '.join(missing)}")


def _require_kpi_table(table, name: str) -> None:
    """Raise TypeError / ValueError if *table* is not a KPI DataFrame."""
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{name} bir pandas DataFrame olmalıdır.")
    missing = [column for column in KPI_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError(f"{name} içinde eksik KPI sütun(lar)ı: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Internal helpers - formatting (rounding happens only here)
# ---------------------------------------------------------------------------

def _row(label: str, value: str) -> str:
    """Return one indented 'label : value' line."""
    return f"  {label:<{LABEL_WIDTH}}: {value}"


def _pct(value) -> str:
    """Format a percentage with 2 decimals ('-' for a missing value)."""
    return "-" if value is None or pd.isna(value) else f"%{value:.2f}"


def _hours(value) -> str:
    """Format hours with up to 3 decimals (e.g. 223.375 saat)."""
    return "-" if value is None or pd.isna(value) else f"{value:.3f}".rstrip("0").rstrip(".") + " saat"


def _section(number: int, title: str) -> list[str]:
    """Return the heading lines of a numbered report section."""
    return [SEPARATOR_THIN, f"{number}. {title}", SEPARATOR_THIN]


def _group_label(value) -> str:
    """Return a table group label (ISO text for dates)."""
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)


def _format_kpi_table(table: pd.DataFrame, title: str) -> list[str]:
    """Return the lines of one KPI table (column-wise formatting, no row loop)."""
    labels = [_group_label(value) for value in table.index.tolist()]
    columns = {column: table[column].tolist() for column in KPI_COLUMNS}
    body = [
        f"  {label:<12}{count:>6}{planned:>11}{actual:>13}{gap:>9}"
        f"{attain:>8.2f}{downtime:>11.3f}{avail:>8.2f}{util:>8.2f}{events:>9}{std:>7.2f}"
        for label, count, planned, actual, gap, attain, downtime, avail, util, events, std in zip(
            labels,
            columns["record_count"],
            columns["total_planned_units"],
            columns["total_actual_units"],
            columns["production_gap"],
            columns["attainment_pct"],
            columns["total_downtime_hours"],
            columns["availability_pct"],
            columns["capacity_utilization_pct"],
            columns["downtime_event_count"],
            columns["attainment_pct_std"],
        )
    ]
    return [title, _TABLE_HEADER, "  " + "-" * (len(_TABLE_HEADER) - 2), *body, ""]


def _format_period_overview(table: pd.DataFrame, title: str, unit: str) -> list[str]:
    """Return a short overview of a long period table (day or week)."""
    attainment = table["attainment_pct"]
    gap = table["production_gap"]
    worst, best, worst_gap = attainment.idxmin(), attainment.idxmax(), gap.idxmin()
    return [
        title,
        _row(f"{unit} sayısı", str(len(table))),
        _row(
            "En düşük gerçekleşme",
            f"{_group_label(worst)} ({_pct(attainment[worst])})",
        ),
        _row(
            "En yüksek gerçekleşme",
            f"{_group_label(best)} ({_pct(attainment[best])})",
        ),
        _row(
            "En büyük üretim açığı",
            f"{_group_label(worst_gap)} ({int(gap[worst_gap])} adet)",
        ),
        f"  Ayrıntı: data/kpi_by_{'day' if unit == 'Gün' else 'week'}.csv",
        "",
    ]


def _others(values: dict, chosen: str, formatter) -> str:
    """Return '(A x, B y, ...)' for the groups other than *chosen*."""
    rest = [f"{key} {formatter(value)}" for key, value in values.items() if key != chosen]
    return f" ({', '.join(rest)})" if rest else ""


def _format_answers(answers: dict) -> list[str]:
    """Return the business question lines (Turkish, rounded for display)."""
    a1, a2, a3 = answers["q1"]["answer"], answers["q2"]["answer"], answers["q3"]["answer"]
    a4, a5, a6 = answers["q4"]["answer"], answers["q5"]["answer"], answers["q6"]["answer"]
    a7 = answers["q7"]["answer"]
    lines: list[str] = []

    def add(key: str, answer_lines: list[str]) -> None:
        lines.append(f"S{key[1:]}. {answers[key]['question']}")
        lines.extend(f"    {text}" for text in answer_lines)
        lines.append("")

    add("q1", [
        f"Yanıt: {a1['machine_id']}, {_pct(a1['attainment_pct'])}"
        f"{_others(a1['values'], a1['machine_id'], _pct)}",
    ])
    add("q2", [
        f"Yanıt: {a2['shift']}, {_pct(a2['availability_pct'])}"
        f"{_others(a2['values'], a2['shift'], _pct)}",
    ])
    q3_lines = [
        f"Toplam duruş: {a3['total_product_code']}, {_hours(a3['total_downtime_hours'])}",
        f"Kayıt başına: {a3['mean_product_code']}, {a3['mean_downtime_hours']:.4f} saat"
        f"{_others(a3['mean_values'], a3['mean_product_code'], lambda v: f'{v:.4f}')}",
    ]
    if a3["total_product_code"] != a3["mean_product_code"]:
        q3_lines.append(
            f"Yorum: {a3['total_product_code']} toplamda önde, ancak kayıt başına "
            f"{a3['mean_product_code']} daha kötü; toplam değer kayıt sayısından etkilenir."
        )
    add("q3", q3_lines)
    q4_lines = [
        f"Yanıt: {_pct(a4['missed_pct'])} ({a4['missed_count']} / {a4['record_count']}); "
        f"en yüksek {a4['machine_id']}, {_pct(a4['machine_missed_pct'])}"
        f"{_others(a4['values'], a4['machine_id'], _pct)}",
    ]
    counts = a4.get("count_values", {})
    if counts:
        most = max(counts, key=counts.get)
        if most != a4["machine_id"]:
            q4_lines.append(
                f"Yorum: Plan kaçıran kayıt sayısı en çok {most} makinesinde ({counts[most]} kayıt), "
                f"ancak oran olarak {a4['machine_id']} önde; karşılaştırmada oran esas alınır."
            )
    add("q4", q4_lines)
    if a5["week_start"] is None:
        q5_lines = ["Yanıt: Veride tam (7 günlük) hafta bulunmuyor."]
    else:
        q5_lines = [
            f"Yanıt: week_start {a5['week_start']}, {a5['production_gap']} adet "
            f"({a5['complete_week_count']} tam hafta içinde)",
        ]
    add("q5", q5_lines)
    add("q6", [
        f"Yanıt: {a6['machine_id']}, {_pct(a6['capacity_utilization_pct'])}"
        f"{_others(a6['values'], a6['machine_id'], _pct)}",
    ])
    if a7["difference_pct_points"] is None:
        q7_lines = ["Yanıt: Karşılaştırma için hem duruşlu hem duruşsuz kayıt gereklidir."]
    else:
        q7_lines = [
            f"Yanıt: {a7['with_downtime_count']} duruşlu kayıtta "
            f"{_pct(a7['with_downtime_mean_attainment_pct'])}; "
            f"{a7['without_downtime_count']} duruşsuz kayıtta "
            f"{_pct(a7['without_downtime_mean_attainment_pct'])}; "
            f"fark {a7['difference_pct_points']:.2f} puan",
        ]
    add("q7", q7_lines)
    return lines


def _format_cleaning(cleaning_summary: dict) -> list[str]:
    """Return the data quality section lines."""
    issue_counts = cleaning_summary["issue_counts"]
    if not isinstance(issue_counts, dict):
        raise TypeError("issue_counts bir sözlük (dict) olmalıdır.")
    lines = [
        _row("Ham satır sayısı", str(cleaning_summary["raw_row_count"])),
        _row("Temiz satır sayısı", str(cleaning_summary["clean_row_count"])),
        _row("Silinen satır sayısı", str(cleaning_summary["dropped_row_count"])),
        _row("Doldurulan satır sayısı", str(cleaning_summary["filled_row_count"])),
        "  Sorun türleri (temizlik günlüğü satırı):",
    ]
    ordered = [code for code in ISSUE_CODES if issue_counts.get(code)]
    ordered += [code for code in issue_counts if code not in ISSUE_CODES and issue_counts[code]]
    if not ordered:
        lines.append("    Sorunlu kayıt bulunmadı.")
    for code in ordered:  # fixed list of issue codes, not a record loop
        action = ACTION_LABELS.get(ISSUE_ACTIONS.get(code, ""), "-")
        label = ISSUE_LABELS.get(code, code)
        lines.append(f"    {code:<24}: {issue_counts[code]:>4}  ({label}; {action})")
    lines.append(f"  Toplam günlük satırı      : {sum(issue_counts.values())}")
    return lines


# ---------------------------------------------------------------------------
# Public API - report
# ---------------------------------------------------------------------------

def build_analysis_report(
    cleaning_summary: dict, summary: dict, kpi_tables: dict, answers: dict
) -> str:
    """Build the Turkish analysis report as a multi-line string.

    Sections: (1) data quality from ``summarize_cleaning``; (2) general
    result block produced by MP3 ``build_summary_report`` with the machine
    group lines, followed by the extra KPIs of ``summarize_kpi``; (3) KPI
    tables (machine, product, shift in full; day and week as an overview
    when present); (4) answers of ``answer_business_questions``.

    Args:
        cleaning_summary: summarize_cleaning output (raw_row_count,
            clean_row_count, dropped_row_count, filled_row_count,
            issue_counts).
        summary: summarize_kpi output (MP3 summary keys + extras).
        kpi_tables: Dictionary with at least 'machine', 'product', 'shift'
            KPI tables ('day' and 'week' optional).
        answers: answer_business_questions output (q1 ... q7).

    Returns:
        The report text.  Nothing is printed.

    Raises:
        TypeError: If an argument has a wrong type.
        ValueError: If a required key / KPI column is missing.
    """
    _require_dict(cleaning_summary, "cleaning_summary", CLEANING_SUMMARY_KEYS)
    _require_dict(summary, "summary", ())
    _require_dict(kpi_tables, "kpi_tables", REPORT_TABLE_KEYS)
    _require_dict(answers, "answers", QUESTION_KEYS)
    for key in KPI_TABLE_GROUPS:
        if key in kpi_tables:
            _require_kpi_table(kpi_tables[key], f"kpi_tables['{key}']")
    for key in QUESTION_KEYS:
        _require_dict(answers[key], f"answers['{key}']", ("question", "answer"))

    general_block = build_summary_report(
        summary,
        kpi_table_to_group_summaries(kpi_tables["machine"]),
        TABLE_TITLES["machine"],
    )

    lines = [SEPARATOR_THICK, f"{REPORT_TITLE:^{REPORT_WIDTH}}", SEPARATOR_THICK]
    lines += _section(1, "VERİ KALİTESİ")
    lines += _format_cleaning(cleaning_summary)
    lines += _section(2, "GENEL SONUÇ")
    lines += general_block.split("\n")
    lines.append("Ek Göstergeler")
    if "capacity_utilization_pct" in summary:
        lines.append(_row("Kapasite kullanım oranı", _pct(summary["capacity_utilization_pct"])))
    if "downtime_event_count" in summary:
        lines.append(_row("Duruşlu kayıt sayısı", str(summary["downtime_event_count"])))
    if "attainment_pct_std" in summary:
        lines.append(
            _row("Gerçekleşme std (ddof=0)", f"{summary['attainment_pct_std']:.2f} puan")
        )
    lines += _section(3, "KPI TABLOLARI")
    lines.append(
        "  Gerç.% = plan gerçekleşme, Kull.% = kullanılabilirlik, Kap.% = kapasite kullanımı, "
        "Std = gerçekleşme std (ddof=0)"
    )
    lines.append("")
    for key in REPORT_TABLE_KEYS:
        lines += _format_kpi_table(kpi_tables[key], TABLE_TITLES[key])
    if "day" in kpi_tables and not kpi_tables["day"].empty:
        lines += _format_period_overview(kpi_tables["day"], TABLE_TITLES["day"], "Gün")
    if "week" in kpi_tables and not kpi_tables["week"].empty:
        lines += _format_period_overview(kpi_tables["week"], TABLE_TITLES["week"], "Hafta")
    lines += _section(4, "İŞLETME SORULARI")
    lines += _format_answers(answers)
    lines.append(SEPARATOR_THICK)
    return "\n".join(lines)


def print_analysis_report(
    cleaning_summary: dict, summary: dict, kpi_tables: dict, answers: dict
) -> None:
    """Print the report built by build_analysis_report() to stdout."""
    print(build_analysis_report(cleaning_summary, summary, kpi_tables, answers))


# ---------------------------------------------------------------------------
# Public API - file export
# ---------------------------------------------------------------------------

def _dates_to_iso(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy where every datetime64 column is ISO text (YYYY-MM-DD)."""
    date_columns = [
        column for column in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[column])
    ]
    if not date_columns:
        return frame
    return frame.assign(
        **{column: frame[column].dt.strftime("%Y-%m-%d") for column in date_columns}
    )


def _write_csv(frame: pd.DataFrame, path: str, keep_index: bool) -> None:
    """Write *frame* as UTF-8 CSV with ISO dates and unrounded numbers."""
    output = frame.reset_index() if keep_index else frame.reset_index(drop=True)
    _dates_to_iso(output).to_csv(path, index=False, encoding="utf-8", lineterminator="\r\n")


def save_analysis_outputs(
    data_dir: str,
    clean_df,
    cleaning_log_df,
    analysis_df,
    kpi_tables: dict,
    daily_series,
    weekly_summary,
) -> list[str]:
    """Write the analysis CSV files (Section 4) and return their paths.

    Files (UTF-8, header row, ISO dates, values not rounded):
        clean_records.csv     - MP3 CSV format (MP3 save_records_csv after
                                dataframe_to_records; readable by RecordStore)
        cleaning_log.csv      - record_id, issue, action
        analysis_dataset.csv  - clean columns + DERIVED_COLUMNS
        kpi_by_machine.csv, kpi_by_product.csv, kpi_by_shift.csv,
        kpi_by_day.csv, kpi_by_week.csv
                              - group column + KPI_COLUMNS
        daily_series.csv      - production_date + daily series columns
        weekly_summary.csv    - week_start + weekly summary columns

    Args:
        data_dir: Output folder (created if missing).
        clean_df: clean_records output.
        cleaning_log_df: cleaning log DataFrame.
        analysis_df: add_derived_columns output.
        kpi_tables: build_kpi_tables output (machine, product, shift, day,
            week).
        daily_series: build_daily_series output.
        weekly_summary: build_weekly_summary output.

    Returns:
        List of written file paths in the order above.

    Raises:
        TypeError: If data_dir is not a str / PathLike or a frame argument
            is not a DataFrame.
        ValueError: If data_dir is empty, a KPI table is missing, a clean
            record fails MP3 validation or the folder is not writable.
    """
    if not isinstance(data_dir, (str, os.PathLike)):
        raise TypeError("data_dir metin (str) olmalıdır.")
    folder = os.fspath(data_dir)
    if not str(folder).strip():
        raise ValueError("data_dir boş olamaz.")
    frames = {
        "clean_df": clean_df,
        "cleaning_log_df": cleaning_log_df,
        "analysis_df": analysis_df,
        "daily_series": daily_series,
        "weekly_summary": weekly_summary,
    }
    for name, frame in frames.items():
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"{name} bir pandas DataFrame olmalıdır.")
    _require_dict(kpi_tables, "kpi_tables", tuple(KPI_TABLE_GROUPS))
    for key in KPI_TABLE_GROUPS:
        _require_kpi_table(kpi_tables[key], f"kpi_tables['{key}']")

    # MP3 validation of every clean record happens before anything is written.
    records = dataframe_to_records(clean_df)

    paths = {
        "clean": os.path.join(folder, CLEAN_RECORDS_FILENAME),
        "log": os.path.join(folder, CLEANING_LOG_FILENAME),
        "analysis": os.path.join(folder, ANALYSIS_DATASET_FILENAME),
        **{
            f"kpi_{key}": os.path.join(folder, KPI_FILENAME_TEMPLATE.format(key=key))
            for key in KPI_TABLE_GROUPS
        },
        "daily": os.path.join(folder, DAILY_SERIES_FILENAME),
        "weekly": os.path.join(folder, WEEKLY_SUMMARY_FILENAME),
    }
    try:
        os.makedirs(folder, exist_ok=True)
        save_records_csv(paths["clean"], records)
        _write_csv(cleaning_log_df, paths["log"], keep_index=False)
        _write_csv(analysis_df, paths["analysis"], keep_index=False)
        for key in KPI_TABLE_GROUPS:
            _write_csv(kpi_tables[key], paths[f"kpi_{key}"], keep_index=True)
        _write_csv(daily_series, paths["daily"], keep_index=True)
        _write_csv(weekly_summary, paths["weekly"], keep_index=True)
    except OSError as err:
        raise ValueError(f"Analiz dosyaları '{folder}' klasörüne yazılamadı: {err}") from err
    return list(paths.values())


__all__ = [
    "REPORT_TITLE",
    "CLEAN_RECORDS_FILENAME",
    "CLEANING_LOG_FILENAME",
    "ANALYSIS_DATASET_FILENAME",
    "KPI_FILENAME_TEMPLATE",
    "DAILY_SERIES_FILENAME",
    "WEEKLY_SUMMARY_FILENAME",
    "ISSUE_LABELS",
    "build_analysis_report",
    "print_analysis_report",
    "save_analysis_outputs",
]
