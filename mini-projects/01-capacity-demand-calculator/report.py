"""
Report module – formats and prints the production capacity report.

This module takes input data and calculation results, builds a human-readable
Turkish report string, and prints it. The build_report function returns the
report as a string (does not print) so it is testable.

Author: Person C
"""


def build_report(input_data: dict, results: dict) -> str:
    """Build a formatted production capacity report as a multi-line string.

    Parameters
    ----------
    input_data : dict
        Dictionary with keys: working_time_hours, cycle_time_sec,
        efficiency_percent, demand_units.
    results : dict
        Dictionary with keys: theoretical_capacity, effective_capacity,
        utilization_rate_percent, capacity_gap, demand_met, status_message.

    Returns
    -------
    str
        The complete report text (Turkish, user-facing).
    """
    # --- User-facing labels (Turkish) ---
    title = "ÜRETİM KAPASİTE RAPORU"
    lbl_inputs = "Girdiler"
    lbl_results = "Sonuçlar"
    lbl_working_time = "Günlük çalışma süresi"
    lbl_cycle_time = "Çevrim süresi"
    lbl_efficiency = "Verimlilik"
    lbl_demand = "Günlük talep"
    lbl_theoretical = "Teorik kapasite"
    lbl_effective = "Efektif kapasite"
    lbl_utilization = "Kapasite kullanım"
    lbl_gap = "Kapasite farkı"
    lbl_status = "DURUM"

    separator_thick = "=" * 46
    separator_thin = "-" * 46

    lines = [
        separator_thick,
        f"        {title}",
        separator_thick,
        lbl_inputs,
        f"  {lbl_working_time:<22}: {input_data['working_time_hours']:.1f} saat",
        f"  {lbl_cycle_time:<22}: {input_data['cycle_time_sec']:.1f} sn/adet",
        f"  {lbl_efficiency:<22}: %{input_data['efficiency_percent']:.1f}",
        f"  {lbl_demand:<22}: {int(input_data['demand_units'])} adet",
        separator_thin,
        lbl_results,
        f"  {lbl_theoretical:<22}: {results['theoretical_capacity']:.2f} adet/gün",
        f"  {lbl_effective:<22}: {results['effective_capacity']:.2f} adet/gün",
        f"  {lbl_utilization:<22}: %{results['utilization_rate_percent']:.2f}",
        f"  {lbl_gap:<22}: {results['capacity_gap']:.2f} adet/gün",
        separator_thin,
        f"{lbl_status}: {results['status_message']}",
        separator_thick,
    ]

    return "\n".join(lines)


def print_report(input_data: dict, results: dict) -> None:
    """Print the formatted production capacity report to stdout.

    Parameters
    ----------
    input_data : dict
        Dictionary with keys: working_time_hours, cycle_time_sec,
        efficiency_percent, demand_units.
    results : dict
        Dictionary with keys: theoretical_capacity, effective_capacity,
        utilization_rate_percent, capacity_gap, demand_met, status_message.

    Returns
    -------
    None
    """
    print(build_report(input_data, results))
