"""
report.py – Turkish production performance reports for production records.

The build_* functions return the report as a multi-line string (they do
not print) so they can be tested; the print_* functions print that text.
Rounding happens only here; analysis.py returns unrounded numbers.

Target layout (Section 5 of the project plan, Kişi C):

    ==============================================
          ÜRETİM KAYIT PERFORMANS RAPORU
    ==============================================
    Kapsam
      Kayıt sayısı          : 8
      ...
    DURUM: PLAN KARŞILANMADI
    Üretim açığı: 144 adet
    ==============================================

Author: Kişi C
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

from production_records.analysis import SUMMARY_KEYS, calculate_production_gap
from production_records.record import ProductionRecord


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

REPORT_WIDTH: int = 46
SEPARATOR_THICK: str = "=" * REPORT_WIDTH
SEPARATOR_THIN: str = "-" * REPORT_WIDTH
LABEL_WIDTH: int = 22

REPORT_TITLE: str = "ÜRETİM KAYIT PERFORMANS RAPORU"
DEFAULT_GROUP_TITLE: str = "Grup Bazında"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_summary(summary: dict, name: str = "summary") -> None:
    """Ensure *summary* is a dict with every Section 3.4 key.

    Raises:
        TypeError: If *summary* is not a dict.
        ValueError: If a required key is missing.
    """
    if not isinstance(summary, dict):
        raise TypeError(f"Özet ({name}) bir sözlük (dict) olmalıdır.")
    missing = [key for key in SUMMARY_KEYS if key not in summary]
    if missing:
        raise ValueError(f"Özet sözlüğünde eksik anahtar(lar): {', '.join(missing)}")


def _row(label: str, value: str) -> str:
    """Return one indented 'label : value' line with an aligned colon."""
    return f"  {label:<{LABEL_WIDTH}}: {value}"


def _build_status_lines(summary: dict) -> list[str]:
    """Return the status headline and, if there is a gap, its detail line."""
    gap = summary["production_gap"]
    if gap > 0:
        return ["DURUM: PLAN KARŞILANDI", f"Fazla üretim: {gap} adet"]
    if gap == 0:
        return ["DURUM: PLAN TAM OLARAK GERÇEKLEŞTİ"]
    return ["DURUM: PLAN KARŞILANMADI", f"Üretim açığı: {abs(gap)} adet"]


def _build_group_lines(group_summaries: dict, group_title: str) -> list[str]:
    """Return the per-group section lines (title + one line per group)."""
    if not isinstance(group_summaries, dict):
        raise TypeError("Grup özetleri (group_summaries) bir sözlük (dict) olmalıdır.")

    lines = [group_title or DEFAULT_GROUP_TITLE]
    if not group_summaries:
        lines.append("  Gösterilecek grup bulunamadı.")
        return lines

    key_width = max(len(str(key)) for key in group_summaries)
    for key, group in group_summaries.items():
        _check_summary(group, f"grup '{key}'")
        lines.append(
            f"  {str(key):<{key_width}} : "
            f"planlanan {group['total_planned_units']}, "
            f"gerçekleşen {group['total_actual_units']}, "
            f"fark {group['production_gap']}, "
            f"%{group['attainment_pct']:.2f}"
        )
    return lines


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def build_summary_report(
    summary: dict,
    group_summaries: dict | None = None,
    group_title: str = "",
) -> str:
    """Build the production performance report as a multi-line string.

    Args:
        summary: Summary dictionary from analysis.summarize_records().
        group_summaries: Optional ``{group_value: summary}`` dictionary from
            analysis.summarize_by(). If None, the group section is omitted.
        group_title: Title of the group section (e.g. 'Makine Bazında').

    Returns:
        The report text (Turkish, user-facing). Nothing is printed.

    Raises:
        TypeError: If *summary* or *group_summaries* is not a dict.
        ValueError: If a summary dictionary misses a Section 3.4 key.
    """
    _check_summary(summary)

    lines = [
        SEPARATOR_THICK,
        f"      {REPORT_TITLE}",
        SEPARATOR_THICK,
        "Kapsam",
        _row("Kayıt sayısı", str(summary["record_count"])),
        _row("Tarih aralığı", f"{summary['date_from']} – {summary['date_to']}"),
        SEPARATOR_THIN,
        "Genel Sonuçlar",
        _row("Planlanan üretim", f"{summary['total_planned_units']} adet"),
        _row("Gerçekleşen üretim", f"{summary['total_actual_units']} adet"),
        _row("Üretim farkı", f"{summary['production_gap']} adet"),
        _row("Plan gerçekleşme", f"%{summary['attainment_pct']:.2f}"),
        _row("Toplam duruş", f"{summary['total_downtime_hours']:.2f} saat"),
        _row("Kullanılabilirlik", f"%{summary['availability_pct']:.2f}"),
        SEPARATOR_THIN,
    ]

    if group_summaries is not None:
        lines.extend(_build_group_lines(group_summaries, group_title))
        lines.append(SEPARATOR_THIN)

    lines.extend(_build_status_lines(summary))
    lines.append(SEPARATOR_THICK)
    return "\n".join(lines)


def print_summary_report(
    summary: dict,
    group_summaries: dict | None = None,
    group_title: str = "",
) -> None:
    """Print the report built by build_summary_report() to stdout.

    Args:
        summary: Summary dictionary from analysis.summarize_records().
        group_summaries: Optional dictionary from analysis.summarize_by().
        group_title: Title of the group section.
    """
    print(build_summary_report(summary, group_summaries, group_title))


# ---------------------------------------------------------------------------
# Record listing (menu option 2)
# ---------------------------------------------------------------------------

_TABLE_HEADER: str = (
    f"{'No':>4}  {'Tarih':<10}  {'Vardiya':<9}  {'Makine':<6}  {'Ürün':<6}  "
    f"{'Plan':>6}  {'Gerçek':>6}  {'Fark':>6}  {'Duruş':>6}"
)


def build_record_table(records: list) -> str:
    """Build a plain-text table of production records.

    Columns: record number, date, shift, machine, product, planned,
    actual, gap (actual - planned) and downtime hours (2 decimals).

    Args:
        records: List of ProductionRecord objects (may be empty).

    Returns:
        The table text including a record count line. Nothing is printed.

    Raises:
        TypeError: If *records* is not a list or contains a non-record item.
    """
    if not isinstance(records, list):
        raise TypeError("Kayıtlar bir liste (list) olarak verilmelidir.")
    if not records:
        return "Gösterilecek kayıt bulunamadı."

    lines = [_TABLE_HEADER, "-" * len(_TABLE_HEADER)]
    for idx, rec in enumerate(records):
        if not isinstance(rec, ProductionRecord):
            raise TypeError(
                f"Kayıt listesinin {idx}. elemanı ProductionRecord türünde olmalıdır."
            )
        record_no = "-" if rec.record_id is None else str(rec.record_id)
        gap = calculate_production_gap(rec.planned_units, rec.actual_units)
        lines.append(
            f"{record_no:>4}  {rec.production_date.isoformat():<10}  "
            f"{rec.shift.value:<9}  {rec.machine_id:<6}  {rec.product_code:<6}  "
            f"{rec.planned_units:>6}  {rec.actual_units:>6}  {gap:>6}  "
            f"{rec.downtime_hours:>6.2f}"
        )
    lines.append("-" * len(_TABLE_HEADER))
    lines.append(f"Toplam {len(records)} kayıt listelendi.")
    return "\n".join(lines)


def print_record_table(records: list) -> None:
    """Print the table built by build_record_table() to stdout.

    Args:
        records: List of ProductionRecord objects (may be empty).
    """
    print(build_record_table(records))
