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
- **Integration Guard**: Deserializes products and machines directly using domain classes (`Product`, `Machine`). Line deserialization is completed when Kişi C finalizes `ProductionLine`.

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

The `machine.py` module defines the operational entity `Machine` and state management enum `MachineStatus`.

### 4.1 `MachineStatus` (Enum)
- **Values**: `IDLE = 'idle'`, `RUNNING = 'running'`, `MAINTENANCE = 'maintenance'`, `BROKEN = 'broken'`.
- String-based enum enabling transparent JSON serialization and database storage.

### 4.2 `Machine(FactoryEntity)`
- **Data Contract Attributes**:
  - `machine_id` (str): Unique machine identifier (e.g. `'M1'`). Non-empty.
  - `name` (str): Display name. Non-empty.
  - `working_hours` (float): Daily working time in hours/day (`0 < x <= 24`).
  - `cycle_time_sec` (float): Base cycle time per unit in seconds (`x > 0`).
  - `efficiency_pct` (float): Efficiency as a percentage (`0 < x <= 100`).
  - `maintenance_interval_hours` (float): Interval in operating hours between required maintenance (`x > 0`).
  - `status` (MachineStatus): Current state. Default: `IDLE`.
  - `operating_hours_since_maintenance` (float): Accumulated operating hours since last service (`x >= 0`). Default: `0.0`.
  - `line_id` (str | None): ID of assigned production line. Default: `None`.

### 4.3 Methods & Behaviors
- **`set_status(new_status: MachineStatus) -> None`**: Enforces the state transition matrix from Section 3.5. Same-state transitions are treated as no-op. Invalid transitions raise `ValueError` with clear Turkish error messages.
- **`is_available() -> bool`**: Returns `True` if status is `IDLE` or `RUNNING`.
- **`get_theoretical_capacity(cycle_time_sec: float | None = None) -> float`**: Independent of machine status. Calls `calculations.theoretical_capacity`. Supports overriding cycle time for product-specific capacity.
- **`get_effective_capacity(cycle_time_sec: float | None = None) -> float`**: Returns `0.0` when unavailable (`MAINTENANCE` or `BROKEN`). Calls `calculations.effective_capacity` when available.
- **`needs_maintenance() -> bool`**: Returns `True` when `operating_hours_since_maintenance >= maintenance_interval_hours`.
- **`add_operating_hours(hours: float) -> None`**: Only allowed while machine status is `RUNNING` and `hours > 0`.
- **`perform_maintenance() -> None`**: Only allowed in `MAINTENANCE` state. Resets counter to `0.0` and transitions status to `IDLE`.
- **`to_dict() -> dict`** & **`from_dict(cls, data: dict) -> Machine`**: Full serialization support adhering to Section 3.4.

### 4.4 Roadmap & Main Project Usage
- **MP-03 (CSV/JSON)**: Key reference entity in event logs and audit trails.
- **MP-04 & MP-05 (NumPy & Pandas)**: `to_dict()` outputs map cleanly into arrays and DataFrames.
- **MP-07 (SmartFactoryDB)**: Maps directly to the `machines` table; `line_id` acts as a foreign key.
- **MP-13 (Predictive Maintenance)**: `operating_hours_since_maintenance` and `maintenance_interval_hours` serve as model features for failure risk.
- **MP-15 & MP-16 (Scheduling)**: Capacity constraint calculations in solver formulation.
- **MP-17 (Dynamic Rescheduling)**: `set_status(MachineStatus.BROKEN)` triggers instant replanning.

---

## 5. ProductionLine & Integration Module (`factory_model/production_line.py`, `factory_model/sample_data.py`, `main.py`) — Kişi C

The `production_line.py` module defines the aggregate entity `ProductionLine`, product-line matching utilities, and factory construction routines.

### 5.1 `ProductionLine(FactoryEntity)`
- **Data Contract Attributes**:
  - `line_id` (str): Unique line identifier (e.g. `'L1'`). Non-empty.
  - `name` (str): Display name. Non-empty.
  - `machines` (list[Machine]): List of assigned `Machine` instances (internal collection).
  - `compatible_product_codes` (set[str]): Set of product codes (`product_code`) compatible with this line.
- **Methods & Behaviors**:
  - `add_machine(machine: Machine) -> None`: Adds a machine to the line and automatically sets `machine.line_id = self.line_id`.
    - Raises `TypeError` if `machine` is not a `Machine` instance.
    - Raises `ValueError` if the machine is already on this line or already assigned to another line.
  - `remove_machine(machine_id: str) -> Machine`: Removes the machine matching `machine_id` and sets its `line_id = None`. Raises `ValueError` if not found.
  - `get_machine(machine_id: str) -> Machine`: Retrieves a machine by its identifier. Raises `ValueError` if not found.
  - `add_compatible_product(product: Product) -> None`: Registers a product's compatibility by storing its `product_code`. Avoids circular object references. Raises `TypeError` if input is not a `Product`.
  - `is_compatible(product: Product) -> bool`: Checks whether `product.product_code` exists in the compatible product set.
  - `get_available_machines() -> list[Machine]`: Filters and returns machines whose status is `IDLE` or `RUNNING`.
  - `get_effective_capacity(product: Product | None = None) -> float`: Calculates total line effective capacity under the parallel machine assumption.
    - If `product is None`: Sums each available machine's default effective capacity.
    - If `product is not None`: Uses `product.processing_time_sec` as cycle time across all available machines. Raises `ValueError` if the product is not compatible with the line.
  - `get_machines_needing_maintenance() -> list[Machine]`: Returns all machines assigned to this line that require service (`needs_maintenance() == True`).
  - `to_dict() -> dict`: Returns dictionary with keys: `line_id`, `name`, `machine_ids` (list of strings), `compatible_product_codes` (sorted list of strings).
  - `from_dict(cls, data: dict, machines_by_id: dict[str, Machine]) -> ProductionLine`: Deserializes a line dictionary using pre-constructed machine instances from `machines_by_id`. Re-links machines and compatibility codes. Raises `ValueError` if required fields or machine IDs are missing.
  - `__repr__() -> str`: Human-readable summary including line ID, name, machine count/IDs, and compatible product codes.

### 5.2 Helper Function: `find_lines_for_product`
- **Signature**: `find_lines_for_product(product: Product, lines: list[ProductionLine]) -> list[ProductionLine]`
- **Purpose**: Filters the provided list of production lines to find all lines capable of manufacturing the specified product.
- **Returns**: List of matching `ProductionLine` objects.

### 5.3 Sample Factory Builder (`factory_model/sample_data.py`)
- **`build_sample_factory() -> dict`**:
  - Constructs the reference layout specified in Section 7.1: 3 products (`P-A`, `P-B`, `P-C`), 5 machines (`M1`–`M5`), and 3 lines (`L1`–`L3`).
  - Returns `{'products': [...], 'machines': [...], 'lines': [...]}`.

### 5.4 Demo Runner (`main.py`)
- **Workflow**:
  1. Instantiates sample factory via `build_sample_factory()`.
  2. Prints line statuses, machine allocations, and theoretical/effective capacities.
  3. Lists machines exceeding maintenance thresholds.
  4. Simulates machine breakdown (`BROKEN`), illustrates line capacity reduction, initiates maintenance (`MAINTENANCE` -> `perform_maintenance()`), and demonstrates full capacity recovery.
  5. Outputs product-line compatibility matrix and available routing options.
  6. Exports snapshot to `data/sample_factory.json`.

### 5.5 Roadmap & Main Project Usage
- **MP-03 (CSV/JSON)**: Defines foreign key relations (`machine.line_id`, `line_products`).
- **MP-07 (SmartFactoryDB)**: Maps directly to `production_lines` table and `line_products` junction table.
- **MP-15 & MP-16 (OR-Tools / Scheduling)**: `line.get_effective_capacity(product)` serves as the primary capacity constraint; `find_lines_for_product()` generates the routing feasibility matrix.
- **MP-17 (Dynamic Rescheduling)**: Instant recomputation of `get_effective_capacity()` upon machine status change without any hidden state.
- **MP-18 (SimPy Simulation)**: ProductionLine acts as the composite resource dispatching work to machine queues.
- **MP-19 & MP-21 (Streamlit & FastAPI)**: Serves as the core business logic layer for web dashboard widgets and REST endpoints.

