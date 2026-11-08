"""
dataset.py - Raw dataset pipeline: MP4 simulation + MP3 RecordStore.

Plan Section 3.1 data flow (Kişi A part):

    MP4 SimulationConfig.from_factory -> simulate -> simulation_to_records
      -> MP3 RecordStore.add_records -> raw_records_clean.csv (600 rows)
      -> inject_faults (seed 42) -> raw_records_dirty.csv / .json (610 rows)
                                  + fault_injection_log.csv (76 rows)

No new production or capacity algorithm is written here: the raw records
come unchanged from the MP4 bridge and the record ids are assigned by the MP3
RecordStore.  The only new randomness is in fault_injection.py.

No print/input; error messages are Turkish.

Author: Kişi A
Mini Project: 05 - Production Data Analysis with Pandas
"""
from __future__ import annotations

import os

from capacity_simulation.export import simulation_to_records
from capacity_simulation.generation import simulate
from capacity_simulation.models import SimulationConfig
from production_analysis.fault_injection import inject_faults, save_dirty_records
from production_analysis.loading import load_records_dataframe
from production_analysis.masters import build_machine_master, build_product_master
from production_records.record_store import RecordStore

# ---------------------------------------------------------------------------
# Constants (plan Section 4 file names)
# ---------------------------------------------------------------------------

#: Default number of simulated days (4 machines x 120 days -> 600 records).
DEFAULT_DATASET_DAYS: int = 120

#: Default seed of the simulation and of the fault injection.
DEFAULT_DATASET_SEED: int = 42

RAW_CLEAN_FILENAME: str = "raw_records_clean.csv"
DIRTY_CSV_FILENAME: str = "raw_records_dirty.csv"
DIRTY_JSON_FILENAME: str = "raw_records_dirty.json"
FAULT_LOG_FILENAME: str = "fault_injection_log.csv"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_clean_records(factory: dict, days: int = 120, seed: int = 42) -> list:
    """Build the raw production records with the MP4 simulation bridge.

    Steps: ``SimulationConfig.from_factory`` (available machines, ordered by
    machine_id) -> ``simulate`` -> ``simulation_to_records`` (one MP3
    ProductionRecord per shift).  record_id is not assigned yet (None).

    Args:
        factory: ``load_factory_json`` output (MP2).
        days: Number of simulated days (default 120).
        seed: Simulation seed (default 42).

    Returns:
        List of ProductionRecord objects ordered by day, machine and shift.

    Raises:
        TypeError / ValueError: Propagated from the MP4 functions (Turkish
            messages), e.g. invalid days/seed or a non-integer shift count.
    """
    config = SimulationConfig.from_factory(factory, days=days, seed=seed)
    result = simulate(config)
    return simulation_to_records(result, factory)


def write_raw_datasets(factory: dict, data_dir: str, days: int = 120, seed: int = 42) -> dict:
    """Write the clean raw set, the dirty CSV/JSON sets and the fault log.

    1. ``raw_records_clean.csv`` is (re)created through MP3
       ``RecordStore.add_records`` (ids 1..n, MP3 CSV format, machine and
       product ids checked against the master tables).  An existing file is
       replaced, because RecordStore would otherwise append to it.
    2. The clean file is loaded with ``load_records_dataframe`` and
       ``inject_faults(clean_df, seed)`` creates the dirty frame and the log.
    3. ``save_dirty_records`` writes ``raw_records_dirty.csv`` / ``.json``;
       the log is written to ``fault_injection_log.csv`` (record_id,
       fault_type).

    Args:
        factory: ``load_factory_json`` output (MP2).
        data_dir: Output folder (created if missing).
        days: Number of simulated days (default 120).
        seed: Seed of the simulation and the fault injection (default 42).

    Returns:
        ``{'clean_path', 'dirty_csv_path', 'dirty_json_path', 'fault_log_path',
        'row_counts'}`` where row_counts is
        ``{'clean': int, 'dirty': int, 'fault_log': int}`` (600, 610, 76 for
        the defaults).

    Raises:
        TypeError: If *data_dir* is not a str or an argument has a wrong type.
        ValueError: If *data_dir* is empty or a step fails validation.
    """
    if not isinstance(data_dir, (str, os.PathLike)):
        raise TypeError("data_dir metin (str) olmalıdır.")
    folder = os.fspath(data_dir)
    if not str(folder).strip():
        raise ValueError("data_dir boş olamaz.")

    records = build_clean_records(factory, days=days, seed=seed)
    machine_ids = set(build_machine_master(factory)["machine_id"].tolist())
    product_codes = set(build_product_master(factory)["product_code"].tolist())

    os.makedirs(folder, exist_ok=True)
    clean_path = os.path.join(folder, RAW_CLEAN_FILENAME)
    dirty_csv_path = os.path.join(folder, DIRTY_CSV_FILENAME)
    dirty_json_path = os.path.join(folder, DIRTY_JSON_FILENAME)
    fault_log_path = os.path.join(folder, FAULT_LOG_FILENAME)

    if os.path.exists(clean_path):
        os.remove(clean_path)
    store = RecordStore(
        clean_path,
        valid_machine_ids=machine_ids,
        valid_product_codes=product_codes,
    )
    store.add_records(records)

    clean_df = load_records_dataframe(clean_path)
    dirty_df, fault_log_df = inject_faults(clean_df, seed=seed)
    save_dirty_records(dirty_df, dirty_csv_path, dirty_json_path)
    fault_log_df.to_csv(fault_log_path, index=False, encoding="utf-8", lineterminator="\r\n")

    return {
        "clean_path": clean_path,
        "dirty_csv_path": dirty_csv_path,
        "dirty_json_path": dirty_json_path,
        "fault_log_path": fault_log_path,
        "row_counts": {
            "clean": len(clean_df),
            "dirty": len(dirty_df),
            "fault_log": len(fault_log_df),
        },
    }


__all__ = [
    "DEFAULT_DATASET_DAYS",
    "DEFAULT_DATASET_SEED",
    "RAW_CLEAN_FILENAME",
    "DIRTY_CSV_FILENAME",
    "DIRTY_JSON_FILENAME",
    "FAULT_LOG_FILENAME",
    "build_clean_records",
    "write_raw_datasets",
]
