"""
main.py – Demo program for Mini Project 02: Factory Object Model.

Builds the sample factory, displays capacity reports, demonstrates
status changes and maintenance, prints the product-line compatibility
matrix, and saves the factory to JSON.

All user-facing text is in Turkish.  No print or input inside classes.

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

import os
import sys

# Ensure the project root is on the path so the package is importable.
sys.path.insert(0, os.path.dirname(__file__))

from factory_model.machine import MachineStatus
from factory_model.production_line import find_lines_for_product
from factory_model.sample_data import build_sample_factory
from factory_model.serialization import save_factory_json


def main() -> None:
    """Run the full factory demo."""

    separator = "=" * 60
    thin_sep = "-" * 60

    print(separator)
    print("  Mini Proje 2 – Fabrika Nesne Modeli Demo")
    print(separator)

    # ------------------------------------------------------------------ #
    # 1. Build the sample factory
    # ------------------------------------------------------------------ #
    factory = build_sample_factory()
    products = factory["products"]
    machines = factory["machines"]
    lines = factory["lines"]

    # ------------------------------------------------------------------ #
    # 2. Print each line: machines, statuses, capacities
    # ------------------------------------------------------------------ #
    print("\n>>> Hat Bilgileri ve Kapasiteler\n")

    for line in lines:
        print(f"Hat: {line.name} ({line.line_id})")
        print(thin_sep)

        for m in line.get_available_machines() + [
            m for m in machines
            if m.line_id == line.line_id and not m.is_available()
        ]:
            # Avoid duplicate printing – collect all machines for this line
            pass

        # Print all machines for the line (use internal list via to_dict)
        line_dict = line.to_dict()
        for mid in line_dict["machine_ids"]:
            m = line.get_machine(mid)
            eff = m.get_effective_capacity()
            theo = m.get_theoretical_capacity()
            print(
                f"  {m.machine_id} ({m.name}): "
                f"Durum={m.status.value}, "
                f"Teorik={theo:.0f} adet/gün, "
                f"Efektif={eff:.0f} adet/gün"
            )

        total = line.get_effective_capacity()
        print(f"  → Hat toplam efektif kapasite: {total:.0f} adet/gün")
        print()

    # ------------------------------------------------------------------ #
    # 3. List machines needing maintenance
    # ------------------------------------------------------------------ #
    print(">>> Bakım Gereken Makineler\n")

    any_needs = False
    for line in lines:
        needing = line.get_machines_needing_maintenance()
        for m in needing:
            print(
                f"  ⚠ {m.machine_id} ({m.name}) – "
                f"Çalışma: {m.operating_hours_since_maintenance:.0f}h / "
                f"Bakım aralığı: {m.maintenance_interval_hours:.0f}h"
            )
            any_needs = True

    if not any_needs:
        print("  Bakım gereken makine yok.")
    print()

    # ------------------------------------------------------------------ #
    # 4. Demonstrate status change: break a machine, show capacity drop
    # ------------------------------------------------------------------ #
    print(">>> Arıza ve Onarım Senaryosu\n")

    m1 = lines[0].get_machine("M1")
    cap_before = lines[0].get_effective_capacity()
    print(f"L1 kapasite (önce): {cap_before:.0f} adet/gün")

    # Break M1
    m1.set_status(MachineStatus.BROKEN)
    cap_after_break = lines[0].get_effective_capacity()
    print(f"M1 arızaya alındı → L1 kapasite: {cap_after_break:.0f} adet/gün")

    # Repair M1: BROKEN → MAINTENANCE → perform_maintenance()
    m1.set_status(MachineStatus.MAINTENANCE)
    m1.perform_maintenance()
    cap_after_repair = lines[0].get_effective_capacity()
    print(
        f"M1 bakım yapılıp onarıldı → L1 kapasite: "
        f"{cap_after_repair:.0f} adet/gün"
    )

    # Restore M1 to RUNNING and its initial hours for consistency with Section 7.1
    m1.set_status(MachineStatus.RUNNING)
    m1._operating_hours_since_maintenance = 50.0
    print()

    # ------------------------------------------------------------------ #
    # 5. Product–line compatibility matrix
    # ------------------------------------------------------------------ #
    print(">>> Ürün–Hat Uygunluk Tablosu\n")

    header = f"  {'Ürün':<12}"
    for line in lines:
        header += f"{line.line_id:<12}"
    print(header)
    print("  " + "-" * (12 + 12 * len(lines)))

    for p in products:
        row = f"  {p.product_code:<12}"
        for line in lines:
            compat = "✓" if line.is_compatible(p) else "✗"
            row += f"{compat:<12}"
        print(row)

    print()

    # find_lines_for_product demo
    print(">>> Ürünlerin Üretilebileceği Hatlar\n")
    for p in products:
        matching = find_lines_for_product(p, lines)
        line_names = [f"{ln.line_id} ({ln.name})" for ln in matching]
        print(f"  {p.product_code} ({p.name}): {', '.join(line_names)}")
    print()

    # ------------------------------------------------------------------ #
    # 6. Save to JSON
    # ------------------------------------------------------------------ #
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "sample_factory.json")

    save_factory_json(json_path, products, machines, lines)
    print(f">>> Fabrika verisi kaydedildi: {json_path}")
    print()
    print(separator)
    print("  Demo tamamlandı.")
    print(separator)


if __name__ == "__main__":
    main()
