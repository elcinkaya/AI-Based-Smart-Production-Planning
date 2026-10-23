"""
sample_data.py – Build the sample factory from Section 7.1.

Creates 3 products, 5 machines, and 3 production lines exactly as
specified in the project plan tables.

Author: Kişi C
Mini Project: 02 – Production Object Model
"""
from __future__ import annotations

from factory_model.machine import Machine, MachineStatus
from factory_model.product import Product
from factory_model.production_line import ProductionLine


def build_sample_factory() -> dict:
    """Build the sample factory with 3 products, 5 machines, and 3 lines.

    Products, machines, and line assignments are taken directly from
    the Word document Section 7.1 tables.

    Returns:
        Dictionary with keys ``'products'``, ``'machines'``, ``'lines'``,
        each containing a list of the corresponding domain objects.
    """

    # -- Products (Table 4) -------------------------------------------------
    p_a = Product(product_code="P-A", name="Bracket",
                  processing_time_sec=30.0, priority=1)
    p_b = Product(product_code="P-B", name="Shaft",
                  processing_time_sec=45.0, priority=2)
    p_c = Product(product_code="P-C", name="Housing",
                  processing_time_sec=60.0, priority=3)

    products = [p_a, p_b, p_c]

    # -- Machines (Table 5) -------------------------------------------------
    m1 = Machine(
        machine_id="M1", name="CNC Lathe 1",
        working_hours=8, cycle_time_sec=30, efficiency_pct=85,
        maintenance_interval_hours=200,
        status=MachineStatus.RUNNING,
        operating_hours_since_maintenance=50,
    )
    m2 = Machine(
        machine_id="M2", name="CNC Lathe 2",
        working_hours=16, cycle_time_sec=45, efficiency_pct=90,
        maintenance_interval_hours=200,
        status=MachineStatus.IDLE,
        operating_hours_since_maintenance=205,
    )
    m3 = Machine(
        machine_id="M3", name="Milling Machine 1",
        working_hours=8, cycle_time_sec=60, efficiency_pct=70,
        maintenance_interval_hours=300,
        status=MachineStatus.RUNNING,
        operating_hours_since_maintenance=100,
    )
    m4 = Machine(
        machine_id="M4", name="Milling Machine 2",
        working_hours=10, cycle_time_sec=20, efficiency_pct=95,
        maintenance_interval_hours=250,
        status=MachineStatus.BROKEN,
        operating_hours_since_maintenance=10,
    )
    m5 = Machine(
        machine_id="M5", name="Assembly Station",
        working_hours=8, cycle_time_sec=30, efficiency_pct=80,
        maintenance_interval_hours=150,
        status=MachineStatus.IDLE,
        operating_hours_since_maintenance=20,
    )

    machines = [m1, m2, m3, m4, m5]

    # -- Production Lines (Table 6) -----------------------------------------
    # L1: Machining Line – M1, M2 – P-A, P-B
    l1 = ProductionLine(line_id="L1", name="Machining Line")
    l1.add_machine(m1)
    l1.add_machine(m2)
    l1.add_compatible_product(p_a)
    l1.add_compatible_product(p_b)

    # L2: Milling Line – M3, M4 – P-B, P-C
    l2 = ProductionLine(line_id="L2", name="Milling Line")
    l2.add_machine(m3)
    l2.add_machine(m4)
    l2.add_compatible_product(p_b)
    l2.add_compatible_product(p_c)

    # L3: Assembly Line – M5 – P-A, P-C
    l3 = ProductionLine(line_id="L3", name="Assembly Line")
    l3.add_machine(m5)
    l3.add_compatible_product(p_a)
    l3.add_compatible_product(p_c)

    lines = [l1, l2, l3]

    return {
        "products": products,
        "machines": machines,
        "lines": lines,
    }
