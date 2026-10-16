"""
Input module – collects and validates user inputs.

Provides functions to safely obtain numerical inputs from the user with
range validation and Turkish error messages. Re-asks on invalid input
without crashing.

Author: Person A (stub by Person C for integration)
"""


def get_number(prompt: str, min_value: float = None, max_value: float = None,
               min_inclusive: bool = True, max_inclusive: bool = True) -> float:
    """Ask the user until a valid number is entered.

    Warns and re-asks on empty input, letters, or out-of-range values.
    Accepts decimal comma (e.g. 7,5) by converting it to a dot.

    Parameters
    ----------
    prompt : str
        The message shown to the user.
    min_value : float or None
        Minimum allowed value.
    max_value : float or None
        Maximum allowed value.
    min_inclusive : bool
        Whether min_value is inclusive (<=) or exclusive (<).
    max_inclusive : bool
        Whether max_value is inclusive (<=) or exclusive (<).

    Returns
    -------
    float
        The validated number.
    """
    while True:
        raw = input(prompt).strip()
        if not raw:
            print("Hata: Boş giriş yapılamaz. Lütfen bir sayı giriniz.")
            continue

        # Accept decimal comma
        raw = raw.replace(",", ".")

        try:
            value = float(raw)
        except ValueError:
            print("Hata: Geçersiz giriş. Lütfen sayısal bir değer giriniz.")
            continue

        # Range checks
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
                pass  # within range
            elif not max_inclusive and value >= max_value:
                print(f"Hata: Değer {max_value} değerinden küçük olmalıdır.")
                continue

        return value


def get_user_inputs() -> dict:
    """Ask the 4 inputs in order and return the input dictionary.

    Returns the dictionary defined in section 2.3 (input_data):
    - working_time_hours (float): Daily working time in hours (0 < x <= 24)
    - cycle_time_sec (float): Cycle time in seconds per unit (x > 0)
    - efficiency_percent (float): Efficiency as percentage (0 < x <= 100)
    - demand_units (float): Daily demand in units (x >= 0)

    Returns
    -------
    dict
        The input_data dictionary.
    """
    print("\n--- Girdi Bilgileri ---")

    working_time_hours = get_number(
        "Günlük çalışma süresi (saat): ",
        min_value=0, max_value=24,
        min_inclusive=False, max_inclusive=True
    )

    cycle_time_sec = get_number(
        "Çevrim süresi (saniye/adet): ",
        min_value=0,
        min_inclusive=False
    )

    efficiency_percent = get_number(
        "Verimlilik (%, örn. 85): ",
        min_value=0, max_value=100,
        min_inclusive=False, max_inclusive=True
    )

    demand_units = get_number(
        "Günlük talep (adet): ",
        min_value=0,
        min_inclusive=True
    )

    return {
        "working_time_hours": working_time_hours,
        "cycle_time_sec": cycle_time_sec,
        "efficiency_percent": efficiency_percent,
        "demand_units": demand_units,
    }
