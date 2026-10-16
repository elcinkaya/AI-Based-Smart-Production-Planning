"""
generate_data.py – Random Scenario Generator

Generates random valid production scenarios for testing purposes.
Uses random.seed(42) for reproducibility as required by the roadmap
synthetic data rules.

Author: Kişi B
Mini Project: 01 – Capacity Calculator
"""

import json
import random
import os
import sys

# Add parent directory to path so we can import calculations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calculations import calculate


def generate_random_scenario(scenario_id: int) -> dict:
    """Generate a single random valid production scenario.

    Args:
        scenario_id: Sequential ID for naming the scenario.

    Returns:
        Dictionary with 'name', 'input', and 'expected' keys matching
        the scenarios.json format defined in section 5.
    """
    # Generate random valid inputs within accepted ranges
    working_time_hours = round(random.uniform(1, 24), 1)
    cycle_time_sec = round(random.uniform(5, 120), 1)
    efficiency_percent = round(random.uniform(10, 100), 1)

    # Calculate effective capacity first to create realistic demand values
    theo = (working_time_hours * 3600) / cycle_time_sec
    eff = theo * (efficiency_percent / 100)

    # Demand can range from 0 to 1.5x effective capacity (to get both
    # surplus and deficit scenarios)
    demand_units = round(random.uniform(0, eff * 1.5))

    input_data = {
        "working_time_hours": working_time_hours,
        "cycle_time_sec": cycle_time_sec,
        "efficiency_percent": efficiency_percent,
        "demand_units": float(demand_units),
    }

    # Calculate expected results using our calculation module
    results = calculate(input_data)

    return {
        "name": f"Random Scenario {scenario_id}",
        "input": input_data,
        "expected": {
            "theoretical_capacity": round(results["theoretical_capacity"], 2),
            "effective_capacity": round(results["effective_capacity"], 2),
            "utilization_rate_percent": round(results["utilization_rate_percent"], 2),
            "capacity_gap": round(results["capacity_gap"], 2),
            "demand_met": results["demand_met"],
        },
    }


def generate_scenarios(count: int = 10, seed: int = 42) -> list:
    """Generate multiple random scenarios.

    Args:
        count: Number of scenarios to generate (default: 10).
        seed: Random seed for reproducibility (default: 42).

    Returns:
        List of scenario dictionaries.
    """
    random.seed(seed)
    scenarios = []
    for i in range(1, count + 1):
        scenarios.append(generate_random_scenario(i))
    return scenarios


def main():
    """Generate random scenarios and save to a JSON file."""
    scenarios = generate_scenarios(count=10, seed=42)

    output_path = os.path.join(os.path.dirname(__file__), "random_scenarios.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)

    print(f"{len(scenarios)} adet rastgele senaryo üretildi.")
    print(f"Dosya: {output_path}")
    print(f"Random seed: 42 (tekrarlanabilir)")

    # Print a summary
    met_count = sum(1 for s in scenarios if s["expected"]["demand_met"])
    not_met_count = len(scenarios) - met_count
    print(f"\nÖzet: {met_count} senaryo karşılanıyor, {not_met_count} senaryo karşılanmıyor.")


if __name__ == "__main__":
    main()
