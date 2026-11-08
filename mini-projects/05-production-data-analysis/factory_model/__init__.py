# factory_model package – public exports managed by Kişi C.
"""
factory_model – Domain model for the smart production planning system.

Exposes the core entity classes and serialization utilities.
"""
from __future__ import annotations

from factory_model.base import FactoryEntity, validate_non_empty_str, validate_number
from factory_model.product import Product
from factory_model.machine import Machine, MachineStatus
from factory_model.production_line import ProductionLine, find_lines_for_product
from factory_model.sample_data import build_sample_factory
from factory_model import serialization

__all__ = [
    # Base
    "FactoryEntity",
    "validate_non_empty_str",
    "validate_number",
    # Product
    "Product",
    # Machine
    "Machine",
    "MachineStatus",
    # ProductionLine
    "ProductionLine",
    "find_lines_for_product",
    # Sample data
    "build_sample_factory",
    # Serialization module
    "serialization",
]
