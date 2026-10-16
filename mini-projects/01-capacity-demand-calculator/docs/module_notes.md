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
