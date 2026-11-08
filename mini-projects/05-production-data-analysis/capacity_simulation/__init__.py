# capacity_simulation package - public exports managed by Kişi C.
"""
capacity_simulation - NumPy based capacity and efficiency simulation.

Exposes the configuration/result models and vectorized capacity functions
(Kişi A), random generation and simulate() (Kişi B), and statistics,
reports, file export, the MP3 record bridge and the speed comparison
(Kişi C) of Mini Project 04.

Mini Project: 04 - Capacity and Efficiency Simulation
"""
from __future__ import annotations

# Models and vectorized capacity (Kişi A)
from capacity_simulation.models import (
    DEFAULT_DAYS,
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    DOWNTIME_HOURS_RANGE,
    DOWNTIME_PROBABILITY,
    DOWNTIME_STEP_HOURS,
    EFFICIENCY_DOWN_PCT,
    EFFICIENCY_UP_PCT,
    LOAD_FACTOR_RANGE,
    PERFORMANCE_FACTOR_RANGE,
    SimulationConfig,
    SimulationResult,
)
from capacity_simulation.capacity import (
    calculate_effective_capacity_array,
    calculate_theoretical_capacity_array,
)

# Random generation and simulation (Kişi B)
from capacity_simulation.generation import (
    calculate_actual_units,
    calculate_planned_units,
    create_rng,
    generate_downtime_matrix,
    generate_efficiency_matrix,
    generate_load_factor_matrix,
    generate_performance_factor_matrix,
    simulate,
)

# Statistics, report, export and benchmark (Kişi C)
from capacity_simulation.stats import (
    SIMULATION_SUMMARY_KEYS,
    calculate_statistics,
    summarize_by_machine,
    summarize_simulation,
)
from capacity_simulation.report import build_simulation_report, print_simulation_report
from capacity_simulation.export import (
    CSV_COLUMNS,
    load_simulation_npz,
    save_simulation_csv,
    save_simulation_npz,
    simulation_to_records,
    split_units,
)
from capacity_simulation.benchmark import (
    build_benchmark_report,
    compare_loop_and_numpy,
    print_benchmark_report,
)

__all__ = [
    # Constants
    "DEFAULT_DAYS",
    "DEFAULT_SEED",
    "DEFAULT_START_DATE",
    "EFFICIENCY_DOWN_PCT",
    "EFFICIENCY_UP_PCT",
    "LOAD_FACTOR_RANGE",
    "PERFORMANCE_FACTOR_RANGE",
    "DOWNTIME_PROBABILITY",
    "DOWNTIME_HOURS_RANGE",
    "DOWNTIME_STEP_HOURS",
    # Models
    "SimulationConfig",
    "SimulationResult",
    # Capacity
    "calculate_theoretical_capacity_array",
    "calculate_effective_capacity_array",
    # Generation
    "create_rng",
    "generate_efficiency_matrix",
    "generate_load_factor_matrix",
    "generate_downtime_matrix",
    "generate_performance_factor_matrix",
    "calculate_planned_units",
    "calculate_actual_units",
    "simulate",
    # Statistics
    "SIMULATION_SUMMARY_KEYS",
    "calculate_statistics",
    "summarize_simulation",
    "summarize_by_machine",
    # Report
    "build_simulation_report",
    "print_simulation_report",
    # Export and MP3 bridge
    "CSV_COLUMNS",
    "save_simulation_npz",
    "load_simulation_npz",
    "save_simulation_csv",
    "split_units",
    "simulation_to_records",
    # Benchmark
    "compare_loop_and_numpy",
    "build_benchmark_report",
    "print_benchmark_report",
]
