"""
calculations.py – Production Capacity and Demand Fulfillment Calculator

This module contains pure calculation functions for computing theoretical
capacity, effective capacity, utilization rate, capacity gap, and demand
fulfillment status. No I/O operations (print/input) are performed here,
making this module safe to import and reuse in the main project.

Author: Kişi B
Mini Project: 01 – Capacity Calculator
"""


def theoretical_capacity(working_time_hours: float, cycle_time_sec: float) -> float:
    """Calculate theoretical daily capacity.

    Formula: (working_time_hours * 3600) / cycle_time_sec

    Args:
        working_time_hours: Daily working time in hours (0 < value <= 24).
        cycle_time_sec: Cycle time per unit in seconds (value > 0).

    Returns:
        Theoretical capacity in units/day.

    Raises:
        ValueError: If working_time_hours or cycle_time_sec is invalid.
    """
    if not isinstance(working_time_hours, (int, float)):
        raise ValueError("Çalışma süresi sayısal bir değer olmalıdır.")
    if not isinstance(cycle_time_sec, (int, float)):
        raise ValueError("Çevrim süresi sayısal bir değer olmalıdır.")
    if working_time_hours <= 0 or working_time_hours > 24:
        raise ValueError("Günlük çalışma süresi 0 ile 24 saat arasında olmalıdır (0 hariç).")
    if cycle_time_sec <= 0:
        raise ValueError("Çevrim süresi sıfırdan büyük olmalıdır.")

    return (working_time_hours * 3600) / cycle_time_sec


def effective_capacity(theoretical: float, efficiency_percent: float) -> float:
    """Calculate effective (real) daily capacity.

    Formula: theoretical * (efficiency_percent / 100)

    Args:
        theoretical: Theoretical capacity in units/day.
        efficiency_percent: Efficiency as a percentage (0 < value <= 100).

    Returns:
        Effective capacity in units/day.

    Raises:
        ValueError: If theoretical is negative or efficiency_percent is invalid.
    """
    if not isinstance(theoretical, (int, float)):
        raise ValueError("Teorik kapasite sayısal bir değer olmalıdır.")
    if not isinstance(efficiency_percent, (int, float)):
        raise ValueError("Verimlilik sayısal bir değer olmalıdır.")
    if theoretical < 0:
        raise ValueError("Teorik kapasite negatif olamaz.")
    if efficiency_percent <= 0 or efficiency_percent > 100:
        raise ValueError("Verimlilik 0 ile 100 arasında olmalıdır (0 hariç).")

    return theoretical * (efficiency_percent / 100)


def utilization_rate(demand_units: float, effective: float) -> float:
    """Calculate capacity utilization rate as a percentage.

    Formula: (demand_units / effective) * 100

    Args:
        demand_units: Daily demand in units (value >= 0).
        effective: Effective capacity in units/day (value > 0).

    Returns:
        Utilization rate as a percentage.

    Raises:
        ValueError: If demand_units is negative or effective is zero/negative.
    """
    if not isinstance(demand_units, (int, float)):
        raise ValueError("Talep miktarı sayısal bir değer olmalıdır.")
    if not isinstance(effective, (int, float)):
        raise ValueError("Efektif kapasite sayısal bir değer olmalıdır.")
    if demand_units < 0:
        raise ValueError("Talep miktarı negatif olamaz.")
    if effective <= 0:
        raise ValueError("Efektif kapasite sıfırdan büyük olmalıdır.")

    return (demand_units / effective) * 100


def capacity_gap(effective: float, demand_units: float) -> float:
    """Calculate the gap between effective capacity and demand.

    Formula: effective - demand_units
    Positive = surplus, Negative = deficit, Zero = exact balance.

    Args:
        effective: Effective capacity in units/day.
        demand_units: Daily demand in units (value >= 0).

    Returns:
        Capacity gap in units/day.

    Raises:
        ValueError: If effective is negative or demand_units is negative.
    """
    if not isinstance(effective, (int, float)):
        raise ValueError("Efektif kapasite sayısal bir değer olmalıdır.")
    if not isinstance(demand_units, (int, float)):
        raise ValueError("Talep miktarı sayısal bir değer olmalıdır.")
    if effective < 0:
        raise ValueError("Efektif kapasite negatif olamaz.")
    if demand_units < 0:
        raise ValueError("Talep miktarı negatif olamaz.")

    return effective - demand_units


def demand_fulfillment_status(effective: float, demand_units: float) -> tuple:
    """Determine whether demand can be met and provide a status message.

    Uses if/elif/else to distinguish three cases:
    - Capacity surplus (effective > demand)
    - Exact balance (effective == demand)
    - Capacity deficit (effective < demand)

    Args:
        effective: Effective capacity in units/day.
        demand_units: Daily demand in units (value >= 0).

    Returns:
        A tuple (is_met: bool, message: str) where is_met indicates whether
        demand is fulfilled and message is a Turkish decision-support message.

    Raises:
        ValueError: If effective is negative or demand_units is negative.
    """
    if not isinstance(effective, (int, float)):
        raise ValueError("Efektif kapasite sayısal bir değer olmalıdır.")
    if not isinstance(demand_units, (int, float)):
        raise ValueError("Talep miktarı sayısal bir değer olmalıdır.")
    if effective < 0:
        raise ValueError("Efektif kapasite negatif olamaz.")
    if demand_units < 0:
        raise ValueError("Talep miktarı negatif olamaz.")

    gap = effective - demand_units

    if gap > 0:
        # Capacity surplus
        return (True, f"Talep karşılanıyor. Kapasite fazlası: {gap:.2f} adet/gün.")
    elif gap == 0:
        # Exact balance
        return (True, "Talep tam olarak karşılanıyor. Kapasite dengede.")
    else:
        # Capacity deficit
        deficit = abs(gap)
        return (False, f"Talep karşılanamıyor. Kapasite açığı: {deficit:.2f} adet/gün.")


def calculate(input_data: dict) -> dict:
    """Run the full calculation pipeline and return the results dictionary.

    Calls the individual functions in order: theoretical_capacity →
    effective_capacity → utilization_rate → capacity_gap →
    demand_fulfillment_status. Does NOT re-implement any formulas.

    Args:
        input_data: Dictionary with keys defined in section 2.3:
            - working_time_hours (float)
            - cycle_time_sec (float)
            - efficiency_percent (float)
            - demand_units (float)

    Returns:
        Dictionary with keys defined in section 2.3:
            - theoretical_capacity (float)
            - effective_capacity (float)
            - utilization_rate_percent (float)
            - capacity_gap (float)
            - demand_met (bool)
            - status_message (str)

    Raises:
        ValueError: If any input value is invalid (propagated from sub-functions).
        KeyError: If a required key is missing from input_data.
    """
    # Extract inputs
    try:
        wt = input_data["working_time_hours"]
        ct = input_data["cycle_time_sec"]
        eff = input_data["efficiency_percent"]
        dem = input_data["demand_units"]
    except KeyError as e:
        raise KeyError(f"Girdi sözlüğünde gerekli anahtar eksik: {e}")

    # Step 1: Theoretical capacity
    theo = theoretical_capacity(wt, ct)

    # Step 2: Effective capacity
    eff_cap = effective_capacity(theo, eff)

    # Step 3: Utilization rate
    # Special case: if demand is 0, utilization is 0% (no division by zero risk
    # since effective > 0 is guaranteed by validation chain)
    util = utilization_rate(dem, eff_cap)

    # Step 4: Capacity gap
    gap = capacity_gap(eff_cap, dem)

    # Step 5: Demand fulfillment status
    is_met, message = demand_fulfillment_status(eff_cap, dem)

    # Build and return the results dictionary
    results = {
        "theoretical_capacity": theo,
        "effective_capacity": eff_cap,
        "utilization_rate_percent": util,
        "capacity_gap": gap,
        "demand_met": is_met,
        "status_message": message,
    }

    return results
