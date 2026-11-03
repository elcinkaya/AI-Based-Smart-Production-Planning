"""
main.py - Console application of Mini Project 4 (Turkish menu).

Menu (Section 5, Kişi C):
1. Run the default simulation (sample factory, 30 days, seed 42) and
   show the report
2. Run with changed parameters (days and seed asked with MP1 get_number)
3. Save the result (data/simulation_output.npz and .csv)
4. Export the result to the MP3 record file
   (simulation_to_records + RecordStore.add_records)
5. Run the loop / NumPy speed comparison (benchmark.py)
6. Exit

Run from the project folder:  python main.py

Author: Kişi C
Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

import os
import sys

from capacity_simulation.benchmark import compare_loop_and_numpy, print_benchmark_report
from capacity_simulation.export import (
    save_simulation_csv,
    save_simulation_npz,
    simulation_to_records,
)
from capacity_simulation.generation import simulate
from capacity_simulation.models import (
    DEFAULT_DAYS,
    DEFAULT_SEED,
    SimulationConfig,
    SimulationResult,
)
from capacity_simulation.report import print_simulation_report
from capacity_simulation.stats import summarize_by_machine, summarize_simulation
from factory_model.serialization import load_factory_json
from production_records.analysis import summarize_by, summarize_records
from production_records.inputs import get_number
from production_records.record_store import RecordStore
from production_records.report import print_summary_report

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTORY_PATH = os.path.join(DATA_DIR, "sample_factory.json")
NPZ_PATH = os.path.join(DATA_DIR, "simulation_output.npz")
CSV_PATH = os.path.join(DATA_DIR, "simulation_output.csv")
RECORDS_PATH = os.path.join(DATA_DIR, "simulation_records.csv")

MAX_DAYS = 3650

MENU_TEXT = """
==============================================
  KAPASİTE VE VERİMLİLİK SİMÜLASYONU (MP4)
==============================================
1. Varsayılan simülasyonu çalıştır ve raporu göster
2. Parametreleri değiştirerek çalıştır
3. Sonucu dosyaya kaydet (.npz ve .csv)
4. Sonucu MP3 kayıt dosyasına aktar
5. Döngü ile NumPy hız karşılaştırmasını çalıştır
6. Çıkış
----------------------------------------------"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_factory() -> dict:
    """Load the MP2 sample factory (single source of the machine set)."""
    return load_factory_json(FACTORY_PATH)


def run_simulation(factory: dict, days: int = DEFAULT_DAYS, seed: int = DEFAULT_SEED) -> SimulationResult:
    """Build the configuration from the factory, simulate and print the report."""
    config = SimulationConfig.from_factory(factory, days=days, seed=seed)
    result = simulate(config)
    print_simulation_report(summarize_simulation(result), summarize_by_machine(result))
    return result


def ask_int(prompt: str, min_value: int, max_value: int | None = None) -> int:
    """Ask for an integer using the MP1 get_number function (re-asks on decimals)."""
    while True:
        value = get_number(prompt, min_value=min_value, max_value=max_value)
        if float(value).is_integer():
            return int(value)
        print("Hata: Lütfen ondalıksız bir tam sayı giriniz.")


def ensure_result(result: SimulationResult | None, factory: dict) -> SimulationResult:
    """Return *result*; run the default simulation first if there is none."""
    if result is None:
        print("Henüz simülasyon çalıştırılmadı; varsayılan simülasyon çalıştırılıyor.")
        result = run_simulation(factory)
    return result


def save_result(result: SimulationResult) -> None:
    """Save the result as .npz and .csv into data/."""
    save_simulation_npz(NPZ_PATH, result)
    save_simulation_csv(CSV_PATH, result)
    rows = result.get_shape()[0] * result.get_shape()[1]
    print(f"Sonuç kaydedildi:\n  {NPZ_PATH}\n  {CSV_PATH} ({rows} veri satırı)")


def export_to_records(result: SimulationResult, factory: dict) -> None:
    """Convert the result to MP3 records, add them to the record file and report."""
    records = simulation_to_records(result, factory)
    store = RecordStore(RECORDS_PATH)
    added = store.add_records(records)
    print(f"{len(added)} kayıt MP3 kayıt dosyasına eklendi: {RECORDS_PATH}")
    print_summary_report(
        summarize_records(added), summarize_by(added, "machine_id"), "Makine Bazında"
    )


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

    result: SimulationResult | None = None
    while True:
        print(MENU_TEXT)
        choice = input("Seçiminiz (1-6): ").strip()
        try:
            if choice == "1":
                result = run_simulation(factory)
            elif choice == "2":
                days = ask_int(f"Gün sayısı (1-{MAX_DAYS}): ", 1, MAX_DAYS)
                seed = ask_int("Tohum (seed, 0 veya daha büyük tam sayı): ", 0)
                result = run_simulation(factory, days=days, seed=seed)
            elif choice == "3":
                result = ensure_result(result, factory)
                save_result(result)
            elif choice == "4":
                result = ensure_result(result, factory)
                export_to_records(result, factory)
            elif choice == "5":
                print("Hız karşılaştırması çalışıyor (1000 makine × 365 gün)...")
                print_benchmark_report(compare_loop_and_numpy())
            elif choice == "6":
                print("Programdan çıkılıyor. İyi günler!")
                break
            else:
                print("Geçersiz seçim. Lütfen 1 ile 6 arasında bir sayı giriniz.")
        except (ValueError, TypeError, OSError) as err:
            print(f"Hata: {err}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram kullanıcı tarafından sonlandırıldı.")
        sys.exit(0)
