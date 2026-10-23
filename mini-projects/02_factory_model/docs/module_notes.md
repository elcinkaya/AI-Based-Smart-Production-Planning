# Module Notes – Mini Project 02: Factory Object Model

> This document lists reusable classes, functions, and serialization utilities along with their purpose,
> parameters, return values, exceptions, and where they can be used in future mini-projects and the main project.
> Each team member writes their own section.

---

## 1. Base Entity & Validation Helpers (`factory_model/base.py`) — Kişi A

The `base.py` module defines the shared foundational entity `FactoryEntity` and standard validation routines used across the domain model.

### 1.1 Helper Functions

#### `validate_non_empty_str(value, field_name: str) -> str`
- **Purpose**: Ensures a given value is a non-empty string after stripping whitespace.
- **Parameters**:
  - `value`: Any value to validate.
  - `field_name` (str): Label used in exception messages.
- **Returns**: `str` stripped of leading and trailing whitespace.
- **Raises**:
  - `TypeError`: If `value` is not a `str`.
  - `ValueError`: If string is empty or contains only whitespace (Turkish message).
- **Future Usage**: Used by `Product`, `Machine`, and `ProductionLine` to validate identifiers and names.

#### `validate_number(value, field_name: str, lower=None, upper=None, lower_inclusive=True, upper_inclusive=True) -> float`
- **Purpose**: Validates numeric bounds for integers and floats. Explicitly rejects boolean values.
- **Parameters**:
  - `value`: Number to validate (`int` or `float`).
  - `field_name` (str): Label used in error reporting.
  - `lower` (float | None): Optional lower bound.
  - `upper` (float | None): Optional upper bound.
  - `lower_inclusive` (bool): Whether lower bound is inclusive (`>=` vs `>`).
  - `upper_inclusive` (bool): Whether upper bound is inclusive (`<=` vs `<`).
- **Returns**: `float` cast of the validated numeric input.
- **Raises**:
  - `TypeError`: If input is not numeric or is boolean.
  - `ValueError`: If input exceeds the specified bounds (Turkish message).
- **Future Usage**: Standard validator for cycle times, working hours, efficiency percentages, and maintenance counters across all subsequent mini-projects.

### 1.2 Base Class

#### `FactoryEntity`
- **Purpose**: Abstract base class for all factory entities providing uniform naming, representation, and serialization contracts.
- **Attributes**:
  - `name` (str): Validated non-empty display name.
- **Methods**:
  - `to_dict() -> dict`: Abstract method to serialize entity to dictionary. Raises `NotImplementedError` if not overridden.
  - `from_dict(cls, data: dict)`: Abstract class method to restore entity from dictionary. Raises `NotImplementedError` if not overridden.
  - `__repr__() -> str`: Human-readable representation for logging and debugging.

---

## 2. Product Entity (`factory_model/product.py`) — Kişi A

The `Product` class models manufactured items and defines processing times and priority constraints.

### 2.1 Class: `Product(FactoryEntity)`
- **Data Contract Attributes**:
  - `product_code` (str): Unique product identifier (e.g. `'P-A'`). Non-empty.
  - `name` (str): Display name. Non-empty.
  - `processing_time_sec` (float): Processing time per unit in seconds (strictly `> 0`).
  - `priority` (int): Scheduling priority from `1` (highest) to `5` (lowest). Default: `3`. Strictly an integer.
- **Methods**:
  - `to_dict() -> dict`: Returns a dictionary with keys `product_code`, `name`, `processing_time_sec`, `priority`.
  - `from_dict(cls, data: dict) -> Product`: Factory constructor. Raises `ValueError` with `"Eksik alan: <field>"` if any required field is missing.
  - `__repr__() -> str`: Formatted string showing key product properties.
- **Main Project & Roadmap Usage**:
  - **MP-03**: Primary key and product reference in transaction and state records.
  - **MP-07 (SmartFactoryDB)**: Maps directly to the `products` relational table.
  - **MP-15 & MP-16 (OR-Tools / Scheduling)**: `processing_time_sec` is the operation duration; `priority` serves as the objective weight in solver functions.
  - **MP-18 (SimPy)**: Entity generator attribute determining simulation event durations.

---

## 3. Serialization Module (`factory_model/serialization.py`) — Kişi A

The `serialization.py` module handles persistence and interchange formats (JSON and CSV) for factory models.

### 3.1 Functions

#### `factory_to_dict(products: list, machines: list, lines: list) -> dict`
- **Purpose**: Aggregates product, machine, and production line collections into a unified dictionary structure.
- **Keys**: `{'products': [...], 'machines': [...], 'lines': [...]}`.

#### `factory_from_dict(data: dict) -> dict`
- **Purpose**: Reconstructs entities in dependency order (`products` -> `machines` -> `lines`).
- **Integration Guard**: Deserializes products immediately; gracefully handles empty machine/line lists or raises explicit `RuntimeError` if machine/line dictionaries are present before Kişi B and Kişi C complete their classes.

#### `save_factory_json(path: str, products: list, machines: list, lines: list) -> None`
- **Purpose**: Writes serialized factory layout to JSON (`utf-8`, indented, `ensure_ascii=False` to preserve Turkish characters).

#### `load_factory_json(path: str) -> dict`
- **Purpose**: Reads JSON factory definitions and invokes `factory_from_dict`.

#### `export_machines_csv(path: str, machines: list) -> None`
- **Purpose**: Flattens machine instances into a standard CSV file with headers matching the section 3.4 data contract:
  `machine_id,name,working_hours,cycle_time_sec,efficiency_pct,maintenance_interval_hours,status,operating_hours_since_maintenance,line_id`.
- **Roadmap Usage**: Feeds into Pandas analysis (MP-05) and batch pipeline testing.

---

## 4. Machine & MachineStatus Module (`factory_model/machine.py`) — Kişi B
*(To be completed by Kişi B)*

---

## 5. ProductionLine & Integration Module (`factory_model/production_line.py`) — Kişi C
*(To be completed by Kişi C)*
