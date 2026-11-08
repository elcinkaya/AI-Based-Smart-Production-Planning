"""
report.py - Text report of a capacity and efficiency simulation.

build_simulation_report() returns the framed (====) report text and never
prints; print_simulation_report() prints it.  Layout follows Section 5
(Kişi C) of the plan and the MP3 report style: 46-character frame,
22-character label column, numbers rounded only here (2 decimals).

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

from capacity_simulation.stats import (
    SIMULATION_SUMMARY_KEYS,
    STATISTIC_FIELDS,
    STATISTIC_KEYS,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

REPORT_WIDTH: int = 46
SEPARATOR_THICK: str = "=" * REPORT_WIDTH
SEPARATOR_THIN: str = "-" * REPORT_WIDTH
LABEL_WIDTH: int = 22
STAT_LABEL_WIDTH: int = 25

REPORT_TITLE: str = "KAPASİTE VE VERİMLİLİK SİMÜLASYON RAPORU"
MACHINE_SECTION_TITLE: str = "Makine Bazında"

#: Turkish row labels of the statistics table (Section 3.5 statistics keys).
STATISTIC_LABELS: dict[str, str] = {
    "efficiency_pct": "Verimlilik (%)",
    "effective_capacity": "Efektif kapasite (adet)",
    "actual_units": "Gerçekleşen üretim (adet)",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_summary(summary: dict, name: str = "summary") -> None:
    """Ensure *summary* is a dict with every Section 3.5 key.

    Raises:
        TypeError: If *summary* (or its statistics entry) is not a dict.
        ValueError: If a required key is missing.
    """
    if not isinstance(summary, dict):
        raise TypeError(f"Özet ({name}) bir sözlük (dict) olmalıdır.")
    missing = [key for key in SIMULATION_SUMMARY_KEYS if key not in summary]
    if missing:
        raise ValueError(f"Özet sözlüğünde eksik anahtar(lar): {', '.join(missing)}")
    statistics = summary["statistics"]
    if not isinstance(statistics, dict):
        raise TypeError("Özetteki statistics değeri bir sözlük (dict) olmalıdır.")
    for field in STATISTIC_FIELDS:
        block = statistics.get(field)
        if not isinstance(block, dict) or any(key not in block for key in STATISTIC_KEYS):
            raise ValueError(
                f"statistics['{field}'] mean, std, min ve max anahtarlarını içermelidir."
            )


def _row(label: str, value: str) -> str:
    """Return one indented 'label : value' line with an aligned colon."""
    return f"  {label:<{LABEL_WIDTH}}: {value}"


def _build_statistics_lines(statistics: dict) -> list[str]:
    """Return the statistics table (header + one row per field)."""
    header = (
        f"{'':<{STAT_LABEL_WIDTH + 2}}{'Ortalama':>8}{'Std':>9}{'Min':>9}{'Maks':>10}"
    )
    lines = ["İstatistikler (tüm makine-günler)", header]
    for field in STATISTIC_FIELDS:
        block = statistics[field]
        lines.append(
            f"  {STATISTIC_LABELS[field]:<{STAT_LABEL_WIDTH}}"
            f"{block['mean']:>8.2f}{block['std']:>9.2f}"
            f"{block['min']:>9.2f}{block['max']:>10.2f}"
        )
    return lines


def _build_machine_lines(machine_summaries: dict) -> list[str]:
    """Return the per-machine section (title + one line per machine)."""
    if not isinstance(machine_summaries, dict):
        raise TypeError("Makine özetleri (machine_summaries) bir sözlük (dict) olmalıdır.")
    lines = [MACHINE_SECTION_TITLE]
    if not machine_summaries:
        lines.append("  Gösterilecek makine bulunamadı.")
        return lines
    key_width = max(len(str(key)) for key in machine_summaries)
    for machine_id, machine in machine_summaries.items():
        _check_summary(machine, f"makine '{machine_id}'")
        lines.append(
            f"  {str(machine_id):<{key_width}} : "
            f"planlanan {machine['total_planned_units']}, "
            f"gerçekleşen {machine['total_actual_units']}, "
            f"fark {machine['production_gap']}, "
            f"%{machine['attainment_pct']:.2f}"
        )
    return lines


def _build_status_lines(summary: dict) -> list[str]:
    """Return the status headline and, if there is a gap, its detail line."""
    gap = summary["production_gap"]
    if gap > 0:
        return ["DURUM: PLAN KARŞILANDI", f"Fazla üretim: {gap} adet"]
    if gap == 0:
        return ["DURUM: PLAN TAM OLARAK GERÇEKLEŞTİ"]
    return ["DURUM: PLAN KARŞILANMADI", f"Üretim açığı: {abs(gap)} adet"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_simulation_report(summary: dict, machine_summaries: dict | None = None) -> str:
    """Build the simulation report as a multi-line string.

    Args:
        summary: Dictionary from stats.summarize_simulation().
        machine_summaries: Optional dictionary from
            stats.summarize_by_machine(); if None the machine section is
            omitted.

    Returns:
        The report text (Turkish, user-facing). Nothing is printed.

    Raises:
        TypeError: If a summary is not a dict.
        ValueError: If a summary misses a Section 3.5 key.
    """
    _check_summary(summary)

    lines = [
        SEPARATOR_THICK,
        f"  {REPORT_TITLE}",
        SEPARATOR_THICK,
        "Kapsam",
        _row("Makine sayısı", str(summary["machine_count"])),
        _row("Gün sayısı", str(summary["day_count"])),
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
    lines.extend(_build_statistics_lines(summary["statistics"]))
    lines.append(SEPARATOR_THIN)

    if machine_summaries is not None:
        lines.extend(_build_machine_lines(machine_summaries))
        lines.append(SEPARATOR_THIN)

    lines.extend(_build_status_lines(summary))
    lines.append(SEPARATOR_THICK)
    return "\n".join(lines)


def print_simulation_report(summary: dict, machine_summaries: dict | None = None) -> None:
    """Print the report built by build_simulation_report() to stdout.

    Args:
        summary: Dictionary from stats.summarize_simulation().
        machine_summaries: Optional dictionary from stats.summarize_by_machine().
    """
    print(build_simulation_report(summary, machine_summaries))
