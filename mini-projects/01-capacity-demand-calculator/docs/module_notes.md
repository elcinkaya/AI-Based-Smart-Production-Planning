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
# Module Notes – Mini Project 01: Capacity Calculator

> This document records each module's purpose, interface, and notes for
> integration into the main project.  Each team member writes their own
> section; Person C merges them at delivery time.

---

## Input Module (`inputs.py`) — Person A

### Purpose

Collects the four production-capacity parameters from the user via the
console, validates them against the agreed-upon ranges, and returns a
validated dictionary (`input_data`) that matches the data contract in
§ 2.3 of the project plan.

### Public Functions

#### `get_number(prompt, min_value, max_value, min_inclusive, max_inclusive) → float`

| Parameter       | Type          | Description                                     |
|-----------------|---------------|-------------------------------------------------|
| `prompt`        | `str`         | Console prompt shown to the user (include unit) |
| `min_value`     | `float\|None` | Lower bound (`None` = no lower bound)           |
| `max_value`     | `float\|None` | Upper bound (`None` = no upper bound)           |
| `min_inclusive`  | `bool`        | `True` → `>=`; `False` → `>`                    |
| `max_inclusive`  | `bool`        | `True` → `<=`; `False` → `<`                    |

* **Returns:** the validated `float` value.
* **Error handling:** never raises; loops until a valid value is entered.
* **Special:** converts decimal commas (`7,5` → `7.5`).

#### `get_user_inputs() → dict`

Calls `get_number` four times with the correct ranges and returns:

```python
{
    "working_time_hours": float,  # hours/day,   0 < x ≤ 24
    "cycle_time_sec":     float,  # sec/unit,    x > 0
    "efficiency_percent": float,  # percent,     0 < x ≤ 100
    "demand_units":       float,  # units/day,   x ≥ 0
}
```

* **Returns:** `dict` with exactly those four keys (see § 2.3).
* **No exceptions** propagate out of this function.

### Units

| Key                  | Unit          | Constraint    |
|----------------------|---------------|---------------|
| `working_time_hours` | hours / day   | 0 < x ≤ 24   |
| `cycle_time_sec`     | seconds / unit| x > 0         |
| `efficiency_percent` | percent (%)   | 0 < x ≤ 100  |
| `demand_units`       | units / day   | x ≥ 0         |

### Where It Can Be Used in the Main Project

* **Mini Project 2 (OOP model):** `Machine.__init__` can call
  `get_user_inputs()` or accept its output directly.
* **Mini Project 19 (Streamlit):** Replace console `input()` calls with
  Streamlit widgets; the validation logic (ranges, types) stays the same.
* **Mini Project 21 (FastAPI):** `get_number` logic translates directly
  to Pydantic field validators.
* **i18n readiness:** All user-facing strings (prompts, error messages)
  are gathered at the top of each function, making future
  internationalisation straightforward.

### Tests

`tests/test_inputs.py` — 18 test cases covering:

| Category               | Examples tested                        |
|------------------------|----------------------------------------|
| Happy path             | integer, dot-decimal, comma-decimal    |
| Empty input            | just Enter                             |
| Non-numeric            | `abc`, `8h`                            |
| Negative values        | `-5`, `-50`                            |
| Zero (exclusive)       | `0` for working_time, cycle_time       |
| Over upper bound       | `25` (hours), `120` (efficiency)       |
| Boundary values        | `24`, `100`, `0` (demand), `0.1`       |
| Multiple retries       | several bad inputs then a valid one    |
| Dict key correctness   | exact keys from § 2.3                  |
| Return type            | all values are `float`                 |

---

## Calculation Module (`calculations.py`) — Person B

*(To be completed by Person B)*

---

## Report Module (`report.py`) — Person C

*(To be completed by Person C)*
