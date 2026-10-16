# Module Notes – Mini Project 01: Capacity Calculator

> This document lists reusable functions and modules along with their purpose,
> parameters, return values, exceptions, and where they can be used in the
> main project. Each team member writes their own section.

---

## Calculation Module (`calculations.py`) — Kişi B

This module is a **pure calculation library** with no I/O operations.
It can be imported directly into the main project without modification.

### Functions

#### `theoretical_capacity(working_time_hours, cycle_time_sec) → float`

| Item | Detail |
|------|--------|
| **Purpose** | Calculate theoretical daily production capacity |
| **Parameters** | `working_time_hours` (float): daily working time in hours (0 < val ≤ 24); `cycle_time_sec` (float): cycle time per unit in seconds (val > 0) |
| **Returns** | Theoretical capacity in units/day |
| **Raises** | `ValueError` if inputs are out of range or non-numeric |
| **Main project usage** | `Machine` class attribute calculation (MP-02); capacity constraint RHS for OR-Tools (MP-15); baseline for NumPy vectorized version (MP-04) |

#### `effective_capacity(theoretical, efficiency_percent) → float`

| Item | Detail |
|------|--------|
| **Purpose** | Calculate effective (real) daily capacity considering efficiency |
| **Parameters** | `theoretical` (float): theoretical capacity in units/day; `efficiency_percent` (float): efficiency as percentage (0 < val ≤ 100) |
| **Returns** | Effective capacity in units/day |
| **Raises** | `ValueError` if inputs are out of range or non-numeric |
| **Main project usage** | OR-Tools capacity constraint (MP-15); dynamic re-planning after machine failure (MP-17); Streamlit/FastAPI service (MP-19/21) |

#### `utilization_rate(demand_units, effective) → float`

| Item | Detail |
|------|--------|
| **Purpose** | Calculate capacity utilization rate as a percentage |
| **Parameters** | `demand_units` (float): daily demand in units (val ≥ 0); `effective` (float): effective capacity in units/day (val > 0) |
| **Returns** | Utilization rate as percentage |
| **Raises** | `ValueError` if demand is negative or effective is ≤ 0 |
| **Main project usage** | KPI dashboard (MP-06/20); EDA health report (MP-10) |

#### `capacity_gap(effective, demand_units) → float`

| Item | Detail |
|------|--------|
| **Purpose** | Calculate the difference between effective capacity and demand |
| **Parameters** | `effective` (float): effective capacity; `demand_units` (float): daily demand |
| **Returns** | Gap in units/day (positive = surplus, negative = deficit, zero = balance) |
| **Raises** | `ValueError` if either input is negative |
| **Main project usage** | Plan feasibility test in dynamic re-planning (MP-17); alert threshold in Streamlit dashboard (MP-19) |

#### `demand_fulfillment_status(effective, demand_units) → tuple[bool, str]`

| Item | Detail |
|------|--------|
| **Purpose** | Determine if demand can be met and provide a decision-support message |
| **Parameters** | `effective` (float): effective capacity; `demand_units` (float): daily demand |
| **Returns** | `(is_met: bool, message: str)` — three cases: surplus, balance, deficit |
| **Raises** | `ValueError` if either input is negative |
| **Main project usage** | Decision support messages for Streamlit/FastAPI (MP-19/21); SHAP explainability context (MP-22) |

#### `calculate(input_data: dict) → dict`

| Item | Detail |
|------|--------|
| **Purpose** | Run the full calculation pipeline as a single entry point |
| **Parameters** | `input_data` (dict): keys from section 2.3 (`working_time_hours`, `cycle_time_sec`, `efficiency_percent`, `demand_units`) |
| **Returns** | Results dict with keys: `theoretical_capacity`, `effective_capacity`, `utilization_rate_percent`, `capacity_gap`, `demand_met`, `status_message` |
| **Raises** | `ValueError` (from sub-functions), `KeyError` (missing input key) |
| **Main project usage** | Direct service function for FastAPI endpoint (MP-21); Streamlit callback (MP-19); re-invoked after fault in dynamic re-planning (MP-17) |

### Data Files

| File | Purpose |
|------|---------|
| `data/scenarios.json` | 7 hand-verified test scenarios with inputs and expected outputs |
| `data/generate_data.py` | Random scenario generator (seed=42) for extended testing |
| `data/random_scenarios.json` | Generated output from `generate_data.py` (10 scenarios) |

### Design Decisions

1. **No I/O in calculations**: All functions are pure — no `print()` or `input()` calls. This makes them safe to import as a library.
2. **No rounding**: Numbers are returned unrounded; rounding is the report module's responsibility.
3. **Efficiency as percentage**: Efficiency is passed and stored as a percentage (e.g., 85), not as a decimal (0.85), consistent with section 2.1.
4. **Turkish user-facing messages**: `status_message` and `ValueError` messages are in Turkish per section 2.6.
5. **Stateless functions**: No global variables or state. Functions can be called repeatedly (important for MP-17 dynamic re-planning).

---

## Input Module (`inputs.py`) — Kişi A

### `get_number(prompt, min_value, max_value, min_inclusive, max_inclusive) → float`

| Item | Detail |
|------|--------|
| **Purpose** | Safely collect a numerical input from the user with range validation |
| **Parameters** | `prompt` (str): message shown to user; `min_value` / `max_value` (float or None): range bounds; `min_inclusive` / `max_inclusive` (bool): boundary inclusivity |
| **Returns** | float — validated number |
| **Errors** | Re-asks on invalid input (empty, non-numeric, out-of-range). Never crashes. |
| **Main project usage** | CLI interfaces only; web interfaces will use form validation instead |

### `get_user_inputs() → dict`

| Item | Detail |
|------|--------|
| **Purpose** | Collect all 4 production inputs and return the input_data dictionary |
| **Returns** | dict with keys: `working_time_hours`, `cycle_time_sec`, `efficiency_percent`, `demand_units` |
| **Main project usage** | Console entry point; Streamlit/FastAPI endpoints receive data via forms/JSON instead |

---

## Report Module (`report.py`) — Kişi C

### `build_report(input_data: dict, results: dict) → str`

| Item | Detail |
|------|--------|
| **Purpose** | Format input data and calculation results into a human-readable Turkish production capacity report |
| **Parameters** | `input_data` (dict): 4 input keys; `results` (dict): 6 result keys from `calculate()` |
| **Returns** | Multi-line report string |
| **Errors** | None (relies on valid input from calculations module) |
| **Main project usage** | Streamlit (MP-19) or FastAPI (MP-21) endpoints for text-based reports; `status_message` field feeds directly into the decision support component |

### `print_report(input_data: dict, results: dict) → None`

| Item | Detail |
|------|--------|
| **Purpose** | Print the output of `build_report` to stdout |
| **Parameters** | Same as `build_report` |
| **Returns** | None |
| **Main project usage** | Console/CLI interface only; web interfaces use `build_report` directly |

---

## Possible Future Extensions (Not Implemented)

- Multi-machine / multi-line capacity aggregation
- Shift-based calculations (day/night shifts with different efficiencies)
- Batch scenario processing from CSV
- Graphical output (charts)
- Multi-language user messages (i18n)
