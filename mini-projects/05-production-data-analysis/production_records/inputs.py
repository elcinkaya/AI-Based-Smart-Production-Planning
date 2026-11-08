"""
Input module – collects and validates production capacity inputs from the user.

This module is responsible for:
  * Asking the user for numeric values via the console.
  * Converting decimal-comma notation (e.g. "7,5") to a proper float.
  * Enforcing value-range constraints and re-asking on invalid input.
  * Returning a validated input dictionary whose keys match the data
    contract defined in the project plan (section 2.3).

Functions:
    get_number  – generic validated numeric input
    get_user_inputs – collects the four production parameters
"""


def get_number(
    prompt: str,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
) -> float:
    """Ask the user until a valid number is entered.

    Warns and re-asks on empty input, letters, or out-of-range values.
    Accepts decimal comma (e.g. ``7,5``) by converting it to a dot.

    Parameters
    ----------
    prompt : str
        The message displayed to the user (should include the unit hint).
    min_value : float or None
        Lower bound for the accepted value.  ``None`` means no lower bound.
    max_value : float or None
        Upper bound for the accepted value.  ``None`` means no upper bound.
    min_inclusive : bool
        If ``True`` the lower bound is *inclusive* (>=); otherwise *exclusive* (>).
    max_inclusive : bool
        If ``True`` the upper bound is *inclusive* (<=); otherwise *exclusive* (<).

    Returns
    -------
    float
        The validated numeric value entered by the user.

    Raises
    ------
    This function never raises; it keeps asking until a valid value is given.
    """
    while True:
        raw = input(prompt).strip()

        # --- empty input ---
        if not raw:
            print("Hata: Boş giriş yapılamaz. Lütfen bir sayı giriniz.")
            continue

        # --- decimal-comma support ---
        raw = raw.replace(",", ".")

        # --- try to convert to float ---
        try:
            value = float(raw)
        except ValueError:
            print(f"Hata: '{raw}' geçerli bir sayı değil. Lütfen sayısal bir değer giriniz.")
            continue

        # --- range checks ---
        if min_value is not None:
            if min_inclusive and value < min_value:
                print(f"Hata: Değer {min_value} veya daha büyük olmalıdır.")
                continue
            if not min_inclusive and value <= min_value:
                print(f"Hata: Değer {min_value} değerinden büyük olmalıdır.")
                continue

        if max_value is not None:
            if max_inclusive and value > max_value:
                print(f"Hata: Değer {max_value} veya daha küçük olmalıdır.")
                continue
            if not max_inclusive and value < max_value:
                # This branch intentionally left for completeness but the
                # current project only uses inclusive upper bounds.
                pass  # value is within range
            if not max_inclusive and value >= max_value:
                print(f"Hata: Değer {max_value} değerinden küçük olmalıdır.")
                continue

        return value


def get_user_inputs() -> dict:
    """Ask the four production-capacity inputs in order and return the
    ``input_data`` dictionary defined in the project data contract
    (section 2.3).

    Keys returned
    -------------
    working_time_hours : float   – Daily working time  (hours/day,  0 < x ≤ 24)
    cycle_time_sec     : float   – Cycle time          (seconds/unit, x > 0)
    efficiency_percent : float   – Efficiency          (percent,     0 < x ≤ 100)
    demand_units       : float   – Daily demand        (units/day,   x ≥ 0)

    Returns
    -------
    dict
        The validated input dictionary.
    """
    print("\n--- Üretim Verileri Girişi ---\n")

    working_time_hours = get_number(
        prompt="Günlük çalışma süresi (saat): ",
        min_value=0,
        max_value=24,
        min_inclusive=False,   # 0 < x
        max_inclusive=True,    # x ≤ 24
    )

    cycle_time_sec = get_number(
        prompt="Çevrim süresi (saniye/adet): ",
        min_value=0,
        min_inclusive=False,   # x > 0
    )

    efficiency_percent = get_number(
        prompt="Verimlilik (%, ör. 85): ",
        min_value=0,
        max_value=100,
        min_inclusive=False,   # 0 < x
        max_inclusive=True,    # x ≤ 100
    )

    demand_units = get_number(
        prompt="Günlük talep (adet): ",
        min_value=0,
        min_inclusive=True,    # x ≥ 0
    )

    return {
        "working_time_hours": working_time_hours,
        "cycle_time_sec": cycle_time_sec,
        "efficiency_percent": efficiency_percent,
        "demand_units": demand_units,
    }
