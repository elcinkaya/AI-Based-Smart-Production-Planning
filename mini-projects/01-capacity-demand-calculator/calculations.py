"""
Calculation module – pure computation functions for production capacity.

Contains no print() or input() calls. Raises ValueError on invalid data
with Turkish messages. Numbers are returned without rounding; rounding
is done only at the report stage.

Author: Person B (stub by Person C for integration)
"""


def theoretical_capacity(working_time_hours: float,
                         cycle_time_sec: float) -> float:
    """Calculate theoretical capacity in units per day.

    Formula: (working_time_hours * 3600) / cycle_time_sec

    Parameters
    ----------
    working_time_hours : float
        Daily working time in hours.
    cycle_time_sec : float
        Cycle time in seconds per unit.

    Returns
    -------
    float
        Theoretical capacity (units/day).

    Raises
    ------
    ValueError
        If working_time_hours <= 0 or cycle_time_sec <= 0.
    """
    if working_time_hours <= 0:
        raise ValueError("Çalışma süresi sıfırdan büyük olmalıdır.")
    if cycle_time_sec <= 0:
        raise ValueError("Çevrim süresi sıfırdan büyük olmalıdır.")
    return (working_time_hours * 3600) / cycle_time_sec


def effective_capacity(theoretical: float,
                       efficiency_percent: float) -> float:
    """Calculate effective capacity in units per day.

    Formula: theoretical * (efficiency_percent / 100)

    Parameters
    ----------
    theoretical : float
        Theoretical capacity (units/day).
    efficiency_percent : float
        Efficiency as a percentage (e.g. 85 for 85%).

    Returns
    -------
    float
        Effective capacity (units/day).

    Raises
    ------
    ValueError
        If efficiency_percent <= 0 or > 100.
    """
    if efficiency_percent <= 0:
        raise ValueError("Verimlilik sıfırdan büyük olmalıdır.")
    if efficiency_percent > 100:
        raise ValueError("Verimlilik 100'den büyük olamaz.")
    return theoretical * (efficiency_percent / 100)


def utilization_rate(demand_units: float, effective: float) -> float:
    """Calculate capacity utilization rate as a percentage.

    Formula: (demand_units / effective) * 100

    Parameters
    ----------
    demand_units : float
        Daily demand in units.
    effective : float
        Effective capacity (units/day).

    Returns
    -------
    float
        Utilization rate in percent.

    Raises
    ------
    ValueError
        If effective == 0 (division by zero) or demand_units < 0.
    """
    if demand_units < 0:
        raise ValueError("Talep negatif olamaz.")
    if effective == 0:
        raise ValueError("Efektif kapasite sıfır olduğunda kullanım oranı hesaplanamaz.")
    return (demand_units / effective) * 100


def capacity_gap(effective: float, demand_units: float) -> float:
    """Calculate the gap between effective capacity and demand.

    Formula: effective - demand_units
    Positive = surplus, negative = deficit, zero = perfect balance.

    Parameters
    ----------
    effective : float
        Effective capacity (units/day).
    demand_units : float
        Daily demand in units.

    Returns
    -------
    float
        Capacity gap (units/day).
    """
    return effective - demand_units


def demand_fulfillment_status(effective: float,
                              demand_units: float) -> tuple:
    """Determine whether demand can be met and return a status message.

    Uses if/elif/else for three cases: surplus, exact balance, deficit.

    Parameters
    ----------
    effective : float
        Effective capacity (units/day).
    demand_units : float
        Daily demand in units.

    Returns
    -------
    tuple[bool, str]
        (is_met, message) – is_met is True when demand <= effective.
    """
    gap = effective - demand_units

    if gap > 0:
        is_met = True
        message = f"TALEP KARŞILANIYOR\nKapasite fazlası: {gap:.2f} adet/gün"
    elif gap == 0:
        is_met = True
        message = "TALEP KARŞILANIYOR\nTam denge: Kapasite ve talep eşit."
    else:
        is_met = False
        message = (
            f"TALEP KARŞILANMIYOR\n"
            f"Kapasite açığı: {abs(gap):.2f} adet/gün"
        )

    return (is_met, message)


def calculate(input_data: dict) -> dict:
    """Run all calculations and build the results dictionary.

    Calls the individual functions in order; does not re-implement formulas.

    Parameters
    ----------
    input_data : dict
        Dictionary with keys: working_time_hours, cycle_time_sec,
        efficiency_percent, demand_units.

    Returns
    -------
    dict
        Results dictionary with keys: theoretical_capacity, effective_capacity,
        utilization_rate_percent, capacity_gap, demand_met, status_message.

    Raises
    ------
    ValueError
        Propagated from individual calculation functions.
    """
    theo = theoretical_capacity(
        input_data["working_time_hours"],
        input_data["cycle_time_sec"]
    )

    eff = effective_capacity(theo, input_data["efficiency_percent"])

    util = utilization_rate(input_data["demand_units"], eff)

    gap = capacity_gap(eff, input_data["demand_units"])

    is_met, status_msg = demand_fulfillment_status(
        eff, input_data["demand_units"]
    )

    return {
        "theoretical_capacity": theo,
        "effective_capacity": eff,
        "utilization_rate_percent": util,
        "capacity_gap": gap,
        "demand_met": is_met,
        "status_message": status_msg,
    }
