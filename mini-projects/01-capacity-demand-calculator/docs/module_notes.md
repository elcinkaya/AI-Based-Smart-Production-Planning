# Module Notes – Mini Project 1: Production Capacity Calculator

This document lists the functions and modules that can be carried over to
the main project (AI-Based Smart Production Planning and Decision Support System).

---

## Report Module (`report.py`)

**Author:** Person C

### `build_report(input_data: dict, results: dict) -> str`

- **Purpose:** Formats input data and calculation results into a human-readable
  production capacity report (Turkish).
- **Parameters:**
  - `input_data`: dict with keys `working_time_hours`, `cycle_time_sec`,
    `efficiency_percent`, `demand_units`
  - `results`: dict with keys `theoretical_capacity`, `effective_capacity`,
    `utilization_rate_percent`, `capacity_gap`, `demand_met`, `status_message`
- **Returns:** Multi-line report string.
- **Errors:** None (relies on valid input from calculations module).
- **Main project usage:** Can be used in Streamlit (Mini 19) or FastAPI (Mini 21)
  endpoints to generate text-based reports. The `status_message` field feeds
  directly into the decision support component.

### `print_report(input_data: dict, results: dict) -> None`

- **Purpose:** Prints the output of `build_report` to stdout.
- **Parameters:** Same as `build_report`.
- **Returns:** None.
- **Main project usage:** Console/CLI interface only; web interfaces would use
  `build_report` directly.

---

## Calculation Module (`calculations.py`)

**Author:** Person B

### `theoretical_capacity(working_time_hours, cycle_time_sec) -> float`

- **Purpose:** Calculates theoretical capacity (units/day).
- **Formula:** `(working_time_hours * 3600) / cycle_time_sec`
- **Parameters:** `working_time_hours` (float, hours/day), `cycle_time_sec` (float, seconds/unit)
- **Returns:** float (units/day)
- **Errors:** `ValueError` if either parameter ≤ 0.
- **Main project usage:** Used in Machine class (Mini 2), OR-Tools planner (Mini 15),
  dynamic re-planning (Mini 17).

### `effective_capacity(theoretical, efficiency_percent) -> float`

- **Purpose:** Calculates effective capacity accounting for efficiency losses.
- **Formula:** `theoretical * (efficiency_percent / 100)`
- **Parameters:** `theoretical` (float), `efficiency_percent` (float, 0 < x ≤ 100)
- **Returns:** float (units/day)
- **Errors:** `ValueError` if efficiency_percent ≤ 0 or > 100.
- **Main project usage:** Right-hand side of capacity constraint in OR-Tools (Mini 15).

### `utilization_rate(demand_units, effective) -> float`

- **Purpose:** Calculates capacity utilization rate as a percentage.
- **Formula:** `(demand_units / effective) * 100`
- **Returns:** float (percent)
- **Errors:** `ValueError` if effective == 0 or demand_units < 0.

### `capacity_gap(effective, demand_units) -> float`

- **Purpose:** Calculates the difference between capacity and demand.
- **Formula:** `effective - demand_units`
- **Returns:** float (positive = surplus, negative = deficit).

### `demand_fulfillment_status(effective, demand_units) -> tuple[bool, str]`

- **Purpose:** Determines whether demand is met and returns a status message.
- **Returns:** `(is_met: bool, message: str)` with three cases: surplus, balance, deficit.
- **Main project usage:** The `status_message` becomes the decision support message
  in the final system.

### `calculate(input_data: dict) -> dict`

- **Purpose:** Orchestrates all calculations; builds the results dictionary.
- **Returns:** dict with all result keys.
- **Main project usage:** Direct service function for Streamlit (Mini 19) and
  FastAPI (Mini 21). Stateless, so safe to call repeatedly (Mini 17 re-planning).

---

## Input Module (`inputs.py`)

**Author:** Person A

### `get_number(prompt, min_value, max_value, min_inclusive, max_inclusive) -> float`

- **Purpose:** Safely collects a numerical input with range validation.
- **Returns:** float
- **Main project usage:** CLI interfaces; web interfaces will use form validation instead.

### `get_user_inputs() -> dict`

- **Purpose:** Collects all 4 inputs and returns the input_data dictionary.
- **Returns:** dict with keys defined in section 2.3.

---

## Possible Extensions (not implemented, noted for future reference)

- Multiple production lines / machines
- Shift-based calculations
- Batch scenario reading from CSV
- Graphical output (charts)
- Multi-language user messages (i18n)
