"""
main.py – Menu application for Mini Project 03: Production Record System.

On start-up the program asks for the record file path (default
data/records.csv) and builds a RecordStore with the valid machine_id /
product_code sets read from data/sample_factory.json. It then shows a
looping Turkish menu:

    1. Add a new production record
    2. List records (optional filters)
    3. Overall performance summary
    4. Summary by machine / product / day
    5. Generate sample data and write it to the file
    6. Convert the file format (CSV <-> JSON)
    7. Exit

Because RecordStore is stateless (every call reads the file), records
written in an earlier session are available immediately after restart.

All user-facing text is Turkish. print/input are used only here and in
report.py (and in the MP1 inputs.get_number helper).

Author: Kişi C
Mini Project: 03 – Production Record System
"""
from __future__ import annotations

import datetime
import os
import sys
from dataclasses import dataclass
from typing import Callable

# Ensure the project root is on the path so the packages are importable.
PROJECT_DIR: str = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from factory_model.serialization import load_factory_json  # noqa: E402
from production_records.analysis import summarize_by, summarize_records  # noqa: E402
from production_records.generate_records import generate_records  # noqa: E402
from production_records.inputs import get_number  # noqa: E402
from production_records.record import SHIFT_HOURS, ProductionRecord, Shift  # noqa: E402
from production_records.record_store import RecordStore  # noqa: E402
from production_records.report import (  # noqa: E402
    print_record_table,
    print_summary_report,
)
from production_records.storage import convert_records_file  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RECORDS_PATH: str = os.path.join("data", "records.csv")
FACTORY_PATH: str = os.path.join(PROJECT_DIR, "data", "sample_factory.json")
DEFAULT_SAMPLE_START: datetime.date = datetime.date(2026, 10, 1)
MAX_SAMPLE_DAYS: int = 365

SEPARATOR: str = "=" * 46

MENU_ITEMS: tuple[str, ...] = (
    "1. Yeni üretim kaydı ekle",
    "2. Kayıtları listele",
    "3. Genel performans özeti",
    "4. Makine / ürün / gün bazında özet",
    "5. Örnek veri üret ve dosyaya yaz",
    "6. Dosya biçimini dönüştür (CSV ↔ JSON)",
    "7. Çıkış",
)

#: Menu option 4 sub-choices: key -> (group_field, report title).
GROUP_OPTIONS: dict[str, tuple[str, str]] = {
    "1": ("machine_id", "Makine Bazında"),
    "2": ("product_code", "Ürün Bazında"),
    "3": ("production_date", "Gün Bazında"),
}


@dataclass
class AppContext:
    """Objects shared by the menu actions during one program session."""

    store: RecordStore
    factory: dict
    valid_machine_ids: set[str]
    valid_product_codes: set[str]


# ---------------------------------------------------------------------------
# Input helpers (re-ask until the input is valid)
# ---------------------------------------------------------------------------

def parse_iso_date(text: str) -> datetime.date:
    """Parse a strict ISO date (YYYY-MM-DD).

    Raises:
        ValueError: With a Turkish message if the format or date is invalid.
    """
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(
            f"Geçersiz tarih biçimi: '{text}'. Tarih YYYY-MM-DD biçiminde olmalıdır."
        )
    try:
        return datetime.date.fromisoformat(text)
    except ValueError as err:
        raise ValueError(f"Geçersiz takvim tarihi: '{text}'.") from err


def ask_text(prompt: str, default: str | None = None) -> str:
    """Ask for a text value; an empty answer returns *default* (or '')."""
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    return raw


def ask_date(
    prompt: str,
    allow_empty: bool = False,
    default: datetime.date | None = None,
) -> datetime.date | None:
    """Ask for an ISO date until a valid one (or an allowed empty answer) is given."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            if default is not None:
                return default
            if allow_empty:
                return None
            print("Hata: Boş giriş yapılamaz. Lütfen bir tarih giriniz.")
            continue
        try:
            return parse_iso_date(raw)
        except ValueError as err:
            print(f"Hata: {err}")


def ask_shift(prompt: str, allow_empty: bool = False) -> Shift | None:
    """Ask for a shift value (morning / afternoon / night)."""
    valid = ", ".join(s.value for s in Shift)
    while True:
        raw = input(prompt).strip().lower()
        if not raw:
            if allow_empty:
                return None
            print("Hata: Boş giriş yapılamaz. Lütfen bir vardiya giriniz.")
            continue
        try:
            return Shift(raw)
        except ValueError:
            print(f"Hata: Geçersiz vardiya: '{raw}'. Geçerli değerler: {valid}.")


def ask_choice(
    prompt: str,
    valid_values: set[str],
    field_label: str,
    allow_empty: bool = False,
) -> str | None:
    """Ask for one of *valid_values* (case-insensitive); re-ask otherwise."""
    lookup = {value.upper(): value for value in valid_values}
    valid = ", ".join(sorted(valid_values))
    while True:
        raw = input(prompt).strip()
        if not raw:
            if allow_empty:
                return None
            print(f"Hata: Boş giriş yapılamaz. Lütfen bir {field_label} giriniz.")
            continue
        if raw.upper() in lookup:
            return lookup[raw.upper()]
        print(f"Hata: Geçersiz {field_label}: '{raw}'. Geçerli değerler: {valid}.")


def ask_int(
    prompt: str,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
) -> int:
    """Ask for a whole number using MP1 get_number; re-ask on decimals."""
    while True:
        value = get_number(prompt, min_value=min_value, max_value=max_value,
                           min_inclusive=min_inclusive)
        if value.is_integer():
            return int(value)
        print(f"Hata: '{value}' tam sayı değil. Lütfen tam sayı giriniz.")


def ask_yes_no(prompt: str) -> bool:
    """Ask an e/h (evet/hayır) question until a valid answer is given."""
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("e", "evet"):
            return True
        if raw in ("h", "hayır", "hayir"):
            return False
        print("Hata: Lütfen 'e' (evet) veya 'h' (hayır) giriniz.")


def resolve_path(path: str) -> str:
    """Resolve a relative path against the project directory."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(PROJECT_DIR, path))


def swap_extension(path: str) -> str:
    """Return *path* with .csv replaced by .json or vice versa."""
    base, ext = os.path.splitext(path)
    return base + (".json" if ext.lower() == ".csv" else ".csv")


# ---------------------------------------------------------------------------
# Start-up
# ---------------------------------------------------------------------------

def open_store(valid_machine_ids: set[str], valid_product_codes: set[str]) -> RecordStore:
    """Ask for the record file path until a usable RecordStore is created.

    The file is read once (count) so that a corrupt file or an unsupported
    extension is reported here instead of in the middle of a menu action.
    """
    while True:
        raw = ask_text(
            f"Kayıt dosyasının yolu [{DEFAULT_RECORDS_PATH}]: ",
            default=DEFAULT_RECORDS_PATH,
        )
        path = resolve_path(raw)
        try:
            store = RecordStore(path, valid_machine_ids, valid_product_codes)
            count = store.count()
        except (ValueError, TypeError, OSError) as err:
            print(f"Hata: {err}")
            print("Lütfen başka bir dosya yolu giriniz.")
            continue

        print(f"Kayıt dosyası: {path}")
        if os.path.exists(path):
            print(f"Dosyadaki mevcut kayıt sayısı: {count}")
        else:
            print("Dosya henüz yok; ilk kayıt eklendiğinde otomatik oluşturulacak.")
        return store


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def action_add_record(ctx: AppContext) -> None:
    """Menu 1: ask the record fields in order and append the record."""
    print("\n--- Yeni Üretim Kaydı ---")
    production_date = ask_date("Üretim tarihi (YYYY-MM-DD): ")
    shift = ask_shift("Vardiya (morning / afternoon / night): ")
    machine_id = ask_choice(
        f"Makine kimliği ({', '.join(sorted(ctx.valid_machine_ids))}): ",
        ctx.valid_machine_ids, "makine kimliği",
    )

    # Report a duplicate key before asking the remaining fields.
    existing = ctx.store.filter_records(
        date_from=production_date, date_to=production_date,
        machine_id=machine_id, shift=shift,
    )
    if existing:
        print(
            f"Hata: {production_date.isoformat()} tarihinde {shift.value} vardiyası için "
            f"{machine_id} makinesinin kaydı zaten var (kayıt no: {existing[0].record_id}). "
            "Kayıt eklenmedi."
        )
        return

    product_code = ask_choice(
        f"Ürün kodu ({', '.join(sorted(ctx.valid_product_codes))}): ",
        ctx.valid_product_codes, "ürün kodu",
    )
    planned_units = ask_int("Planlanan miktar (adet): ", min_value=0, min_inclusive=False)
    actual_units = ask_int("Gerçekleşen miktar (adet): ", min_value=0)
    downtime_hours = get_number(
        f"Duruş süresi (saat, 0-{SHIFT_HOURS:g}): ",
        min_value=0, max_value=SHIFT_HOURS,
    )

    try:
        record = ProductionRecord(
            production_date=production_date,
            shift=shift,
            machine_id=machine_id,
            product_code=product_code,
            planned_units=planned_units,
            actual_units=actual_units,
            downtime_hours=downtime_hours,
        )
        saved = ctx.store.add_record(record)
    except (ValueError, TypeError) as err:
        print(f"Hata: {err}")
        print("Kayıt eklenmedi.")
        return

    print(f"\nKayıt eklendi. Kayıt numarası: {saved.record_id}")
    print_record_table([saved])


def action_list_records(ctx: AppContext) -> None:
    """Menu 2: list all records, optionally filtered."""
    print("\n--- Kayıt Listesi ---")
    if not ask_yes_no("Filtre uygulamak ister misiniz? (e/h): "):
        print_record_table(ctx.store.get_all())
        return

    print("Boş bırakılan filtre uygulanmaz.")
    while True:
        date_from = ask_date("Başlangıç tarihi (YYYY-MM-DD): ", allow_empty=True)
        date_to = ask_date("Bitiş tarihi (YYYY-MM-DD): ", allow_empty=True)
        if date_from is not None and date_to is not None and date_from > date_to:
            print("Hata: Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            continue
        break
    machine_id = ask_choice(
        f"Makine kimliği ({', '.join(sorted(ctx.valid_machine_ids))}): ",
        ctx.valid_machine_ids, "makine kimliği", allow_empty=True,
    )
    product_code = ask_choice(
        f"Ürün kodu ({', '.join(sorted(ctx.valid_product_codes))}): ",
        ctx.valid_product_codes, "ürün kodu", allow_empty=True,
    )
    shift = ask_shift("Vardiya (morning / afternoon / night): ", allow_empty=True)

    records = ctx.store.filter_records(
        date_from=date_from, date_to=date_to, machine_id=machine_id,
        product_code=product_code, shift=shift,
    )
    print()
    print_record_table(records)


def action_overall_summary(ctx: AppContext) -> None:
    """Menu 3: overall KPI summary of all records."""
    records = ctx.store.get_all()
    if not records:
        print("Henüz kayıt yok. Önce kayıt ekleyin veya örnek veri üretin.")
        return
    print()
    print_summary_report(summarize_records(records))


def action_group_summary(ctx: AppContext) -> None:
    """Menu 4: KPI summary grouped by machine, product or day."""
    records = ctx.store.get_all()
    if not records:
        print("Henüz kayıt yok. Önce kayıt ekleyin veya örnek veri üretin.")
        return

    print("\nGruplama türü:")
    print("  1. Makine")
    print("  2. Ürün")
    print("  3. Gün")
    while True:
        choice = input("Seçiminiz (1-3): ").strip()
        if choice in GROUP_OPTIONS:
            break
        print("Hata: Geçersiz seçim. Lütfen 1, 2 veya 3 giriniz.")

    group_field, title = GROUP_OPTIONS[choice]
    print()
    print_summary_report(
        summarize_records(records), summarize_by(records, group_field), title
    )


def action_generate_sample(ctx: AppContext) -> None:
    """Menu 5: generate seeded synthetic records and add them all at once."""
    print("\n--- Örnek Veri Üretimi ---")
    start_date = ask_date(
        f"Başlangıç tarihi (YYYY-MM-DD) [{DEFAULT_SAMPLE_START.isoformat()}]: ",
        default=DEFAULT_SAMPLE_START,
    )
    days = ask_int(f"Gün sayısı (1-{MAX_SAMPLE_DAYS}): ", min_value=1,
                   max_value=MAX_SAMPLE_DAYS)
    seed = ask_int("Tohum (seed) değeri (ör. 42): ", min_value=0)

    records = generate_records(ctx.factory, start_date, days, seed)
    try:
        saved = ctx.store.add_records(records)
    except (ValueError, TypeError) as err:
        print(f"Hata: {err}")
        print("Hiçbir kayıt yazılmadı.")
        return

    if not saved:
        print("Üretilecek kayıt bulunamadı (uygun makine yok).")
        return
    print(
        f"{len(saved)} kayıt üretildi ve dosyaya yazıldı "
        f"(kayıt no: {saved[0].record_id}–{saved[-1].record_id})."
    )
    print(f"Dosyadaki toplam kayıt sayısı: {ctx.store.count()}")


def action_convert_format(ctx: AppContext) -> None:
    """Menu 6: convert a record file between CSV and JSON."""
    print("\n--- Dosya Biçimi Dönüştürme (CSV ↔ JSON) ---")
    source = resolve_path(ask_text(f"Kaynak dosya [{ctx.store.path}]: ",
                                   default=ctx.store.path))
    if not os.path.exists(source):
        print(f"Hata: Kaynak dosya bulunamadı: {source}")
        return

    default_target = swap_extension(source)
    target = resolve_path(ask_text(f"Hedef dosya [{default_target}]: ",
                                   default=default_target))
    if os.path.exists(target) and not ask_yes_no(
        "Hedef dosya zaten var. Üzerine yazılsın mı? (e/h): "
    ):
        print("Dönüştürme iptal edildi.")
        return

    try:
        count = convert_records_file(source, target)
    except (ValueError, TypeError) as err:
        print(f"Hata: {err}")
        return
    print(f"{count} kayıt dönüştürüldü: {source} → {target}")


MENU_ACTIONS: dict[str, Callable[[AppContext], None]] = {
    "1": action_add_record,
    "2": action_list_records,
    "3": action_overall_summary,
    "4": action_group_summary,
    "5": action_generate_sample,
    "6": action_convert_format,
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def print_menu(ctx: AppContext) -> None:
    """Print the main menu with the active record file."""
    print()
    print(SEPARATOR)
    print("      ÜRETİM KAYIT SİSTEMİ – ANA MENÜ")
    print(SEPARATOR)
    print(f"Aktif dosya: {ctx.store.path}")
    for item in MENU_ITEMS:
        print(f"  {item}")
    print(SEPARATOR)


def main() -> int:
    """Run the menu application.

    Returns:
        Process exit code (0 on normal exit, 1 if the factory file
        cannot be loaded).
    """
    print(SEPARATOR)
    print("  Mini Proje 3 – Üretim Kayıt Sistemi")
    print(SEPARATOR)

    try:
        factory = load_factory_json(FACTORY_PATH)
    except (OSError, ValueError, TypeError, RuntimeError) as err:
        print(f"Hata: Fabrika verisi yüklenemedi ({FACTORY_PATH}): {err}")
        return 1

    valid_machine_ids = {m.machine_id for m in factory["machines"]}
    valid_product_codes = {p.product_code for p in factory["products"]}

    try:
        store = open_store(valid_machine_ids, valid_product_codes)
        ctx = AppContext(store, factory, valid_machine_ids, valid_product_codes)

        while True:
            print_menu(ctx)
            choice = input("Seçiminiz (1-7): ").strip()
            if choice == "7":
                print("Program sonlandırıldı. Kayıtlar dosyada saklanmaktadır.")
                return 0
            action = MENU_ACTIONS.get(choice)
            if action is None:
                print("Hata: Geçersiz seçim. Lütfen 1 ile 7 arasında bir sayı giriniz.")
                continue
            try:
                action(ctx)
            except (ValueError, TypeError, OSError) as err:
                # e.g. a record file corrupted by another program
                print(f"Hata: {err}")
    except (KeyboardInterrupt, EOFError):
        print("\nProgram kullanıcı tarafından sonlandırıldı.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
