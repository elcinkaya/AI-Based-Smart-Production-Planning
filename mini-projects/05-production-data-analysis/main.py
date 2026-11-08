"""
main.py - Console application of Mini Project 5 (Turkish menu).

Menu (plan Section 5, Kişi C):
1. Generate the raw dataset (600 records via MP4 + MP3, then the dirty
   610-row version with seed 42)
2. Load and clean the data (cleaning summary and log)
3. Show the KPI tables (machine, product, shift, day, week)
4. Answer the business questions (q1 ... q7)
5. Save the analysis files (data/*.csv)
6. Run the full pipeline (1 -> 5) and print the report
7. Exit

Menu choices are collected with MP1 ``get_number``.
Run from the project folder:  python main.py

Author: Kişi C
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import os
import sys

from factory_model.serialization import load_factory_json
from production_analysis.cleaning import clean_records, summarize_cleaning
from production_analysis.dataset import (
    DEFAULT_DATASET_DAYS,
    DEFAULT_DATASET_SEED,
    DIRTY_CSV_FILENAME,
    write_raw_datasets,
)
from production_analysis.features import (
    add_derived_columns,
    build_daily_series,
    build_weekly_summary,
)
from production_analysis.kpi import build_kpi_tables, summarize_kpi
from production_analysis.loading import load_records_dataframe
from production_analysis.masters import build_machine_master, build_product_master
from production_analysis.questions import answer_business_questions
from production_analysis.report import (
    SEPARATOR_THIN,
    TABLE_TITLES,
    _format_answers,
    _format_cleaning,
    _format_kpi_table,
    _format_period_overview,
    print_analysis_report,
    save_analysis_outputs,
)
from production_records.inputs import get_number

# ---------------------------------------------------------------------------
# Paths and menu
# ---------------------------------------------------------------------------

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DATA_DIR: str = os.path.join(BASE_DIR, "data")
FACTORY_PATH: str = os.path.join(DATA_DIR, "sample_factory.json")
DIRTY_PATH: str = os.path.join(DATA_DIR, DIRTY_CSV_FILENAME)

MENU_TEXT: str = """
==============================================
  PANDAS İLE ÜRETİM VERİSİ ANALİZİ (MP5)
==============================================
1. Ham veri setini üret (MP4 + MP3 ile 600 kayıt, ardından hatalı sürüm)
2. Veriyi yükle ve temizle (temizlik özeti ve günlük)
3. KPI tablolarını göster (makine, ürün, vardiya, gün, hafta)
4. İşletme sorularını yanıtla
5. Analiz dosyalarını kaydet (data/*.csv)
6. Tüm hattı çalıştır (1 -> 5) ve raporu yazdır
7. Çıkış
----------------------------------------------"""


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def load_factory(factory_path: str = FACTORY_PATH) -> dict:
    """Load the MP2 sample factory (single source of machines and products)."""
    return load_factory_json(factory_path)


def ask_menu_choice() -> int:
    """Read an integer menu choice (1..7) using MP1 ``get_number``."""
    while True:
        value = get_number("Seçiminiz (1-7): ", min_value=1, max_value=7)
        if float(value).is_integer():
            return int(value)
        print("Hata: Lütfen 1 ile 7 arasında bir tam sayı giriniz.")


def generate_raw_data(factory: dict, data_dir: str = DATA_DIR) -> dict:
    """Option 1: generate raw_records_clean.csv, dirty csv/json and fault log."""
    info = write_raw_datasets(
        factory, data_dir, days=DEFAULT_DATASET_DAYS, seed=DEFAULT_DATASET_SEED
    )
    counts = info["row_counts"]
    print(
        f"Ham veri setleri üretildi ({data_dir}):\n"
        f"  Temiz ham veri : {info['clean_path']} ({counts['clean']} satır)\n"
        f"  Kirli CSV      : {info['dirty_csv_path']} ({counts['dirty']} satır)\n"
        f"  Kirli JSON     : {info['dirty_json_path']} ({counts['dirty']} satır)\n"
        f"  Hata günlüğü   : {info['fault_log_path']} ({counts['fault_log']} satır)"
    )
    return info


def load_and_clean(factory: dict, data_dir: str = DATA_DIR) -> dict:
    """Option 2: load raw_records_dirty.csv, clean it and build the features."""
    dirty_path = os.path.join(data_dir, DIRTY_CSV_FILENAME)
    if not os.path.isfile(dirty_path):
        print("Ham kirli veri dosyası bulunamadı; önce üretiliyor...")
        write_raw_datasets(factory, data_dir)

    machine_master = build_machine_master(factory)
    product_master = build_product_master(factory)
    raw_df = load_records_dataframe(dirty_path)
    clean_df, cleaning_log_df = clean_records(raw_df, machine_master, product_master)
    cleaning_summary = summarize_cleaning(raw_df, clean_df, cleaning_log_df)
    analysis_df = add_derived_columns(clean_df, machine_master, product_master)
    daily_series = build_daily_series(analysis_df)
    weekly_summary = build_weekly_summary(analysis_df)
    kpi_tables = build_kpi_tables(analysis_df)
    summary = summarize_kpi(analysis_df)
    answers = answer_business_questions(analysis_df)

    return {
        "raw_df": raw_df,
        "clean_df": clean_df,
        "cleaning_log_df": cleaning_log_df,
        "cleaning_summary": cleaning_summary,
        "analysis_df": analysis_df,
        "daily_series": daily_series,
        "weekly_summary": weekly_summary,
        "kpi_tables": kpi_tables,
        "summary": summary,
        "answers": answers,
    }


def ensure_state(state: dict | None, factory: dict, data_dir: str = DATA_DIR) -> dict:
    """Return *state*; load and clean the dataset first when needed."""
    if state is None:
        print("Veri henüz yüklenip temizlenmedi; otomatik olarak yüklenip temizleniyor...")
        state = load_and_clean(factory, data_dir)
    return state


def print_cleaning_result(state: dict) -> None:
    """Print the cleaning summary and the first rows of the cleaning log."""
    print("\n".join([SEPARATOR_THIN, "VERİ TEMİZLİK ÖZETİ", SEPARATOR_THIN]))
    print("\n".join(_format_cleaning(state["cleaning_summary"])))
    log_df = state["cleaning_log_df"]
    print(f"\nTemizlik günlüğü ({len(log_df)} satır, ilk 10 kayıt):")
    for record_id, issue, action in zip(
        log_df["record_id"].head(10).tolist(),
        log_df["issue"].head(10).tolist(),
        log_df["action"].head(10).tolist(),
    ):
        print(f"  record_id={record_id:>4} | {issue:<24} | {action}")


def print_kpi_tables(state: dict) -> None:
    """Option 3: print the machine, product, shift, day and week KPI tables."""
    tables = state["kpi_tables"]
    lines = [SEPARATOR_THIN, "KPI TABLOLARI", SEPARATOR_THIN]
    for key in ("machine", "product", "shift"):
        lines.extend(_format_kpi_table(tables[key], TABLE_TITLES[key]))
    lines.extend(_format_period_overview(tables["day"], TABLE_TITLES["day"], "Gün"))
    lines.extend(_format_period_overview(tables["week"], TABLE_TITLES["week"], "Hafta"))
    print("\n".join(lines))


def print_business_answers(state: dict) -> None:
    """Option 4: print the seven business questions and their answers."""
    lines = [SEPARATOR_THIN, "İŞLETME SORULARI", SEPARATOR_THIN]
    lines.extend(_format_answers(state["answers"]))
    print("\n".join(lines).rstrip())


def save_outputs(state: dict, data_dir: str = DATA_DIR) -> list[str]:
    """Option 5: write all analysis CSV files and print their paths."""
    paths = save_analysis_outputs(
        data_dir,
        state["clean_df"],
        state["cleaning_log_df"],
        state["analysis_df"],
        state["kpi_tables"],
        state["daily_series"],
        state["weekly_summary"],
    )
    print(f"{len(paths)} analiz dosyası kaydedildi:")
    for path in paths:
        print(f"  {path}")
    return paths


def run_full_pipeline(factory: dict, data_dir: str = DATA_DIR) -> dict:
    """Option 6: run the full pipeline (1 -> 5) and print the report."""
    generate_raw_data(factory, data_dir)
    state = load_and_clean(factory, data_dir)
    paths = save_outputs(state, data_dir)
    state["saved_paths"] = paths
    print()
    print_analysis_report(
        state["cleaning_summary"], state["summary"], state["kpi_tables"], state["answers"]
    )
    return state


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the console menu until the user chooses to exit."""
    try:
        factory = load_factory()
    except (OSError, ValueError, TypeError) as err:
        print(f"Hata: Fabrika dosyası yüklenemedi: {err}")
        return

    state: dict | None = None
    while True:
        print(MENU_TEXT)
        choice = ask_menu_choice()
        try:
            if choice == 1:
                generate_raw_data(factory)
                state = None
            elif choice == 2:
                state = load_and_clean(factory)
                print_cleaning_result(state)
            elif choice == 3:
                state = ensure_state(state, factory)
                print_kpi_tables(state)
            elif choice == 4:
                state = ensure_state(state, factory)
                print_business_answers(state)
            elif choice == 5:
                state = ensure_state(state, factory)
                save_outputs(state)
            elif choice == 6:
                state = run_full_pipeline(factory)
            elif choice == 7:
                print("Programdan çıkılıyor. İyi günler!")
                break
        except (ValueError, TypeError, OSError) as err:
            print(f"Hata: {err}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram kullanıcı tarafından sonlandırıldı.")
        sys.exit(0)
