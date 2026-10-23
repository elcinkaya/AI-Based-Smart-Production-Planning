"""
test_product.py – Unit tests for FactoryEntity (base.py) and Product (product.py).

Covers:
  - FactoryEntity construction and abstract-method behaviour
  - validate_non_empty_str and validate_number helpers
  - Valid Product creation
  - Invalid Product creation (processing_time_sec 0, priority 0/6/2.5/True,
    empty product_code, negative processing_time_sec)
  - to_dict / from_dict round-trip
  - from_dict with missing fields

Author: Kişi A
Mini Project: 02 – Factory Object Model
"""
from __future__ import annotations

import unittest

from factory_model.base import FactoryEntity, validate_non_empty_str, validate_number
from factory_model.product import Product


# ===================================================================
# Validation helper tests
# ===================================================================

class TestValidateNonEmptyStr(unittest.TestCase):
    """Tests for validate_non_empty_str."""

    def test_valid_string(self) -> None:
        self.assertEqual(validate_non_empty_str("hello", "test"), "hello")

    def test_strips_whitespace(self) -> None:
        self.assertEqual(validate_non_empty_str("  hi  ", "test"), "hi")

    def test_empty_string_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_non_empty_str("", "field_x")
        self.assertIn("field_x", str(ctx.exception))

    def test_whitespace_only_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_non_empty_str("   ", "field_x")

    def test_non_string_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            validate_non_empty_str(123, "field_x")

    def test_none_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            validate_non_empty_str(None, "field_x")


class TestValidateNumber(unittest.TestCase):
    """Tests for validate_number."""

    def test_valid_int(self) -> None:
        self.assertEqual(validate_number(10, "x"), 10.0)

    def test_valid_float(self) -> None:
        self.assertEqual(validate_number(3.14, "x"), 3.14)

    def test_bool_rejected(self) -> None:
        with self.assertRaises(TypeError):
            validate_number(True, "x")

    def test_string_rejected(self) -> None:
        with self.assertRaises(TypeError):
            validate_number("abc", "x")

    def test_lower_inclusive(self) -> None:
        self.assertEqual(validate_number(0, "x", lower=0), 0.0)
        with self.assertRaises(ValueError):
            validate_number(-1, "x", lower=0)

    def test_lower_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            validate_number(0, "x", lower=0, lower_inclusive=False)
        self.assertEqual(
            validate_number(0.001, "x", lower=0, lower_inclusive=False), 0.001
        )

    def test_upper_inclusive(self) -> None:
        self.assertEqual(validate_number(100, "x", upper=100), 100.0)
        with self.assertRaises(ValueError):
            validate_number(101, "x", upper=100)

    def test_upper_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            validate_number(100, "x", upper=100, upper_inclusive=False)

    def test_combined_bounds(self) -> None:
        # efficiency_pct style: 0 < x <= 100
        self.assertEqual(
            validate_number(
                50, "eff", lower=0, upper=100,
                lower_inclusive=False, upper_inclusive=True,
            ),
            50.0,
        )

    def test_turkish_error_message(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_number(120, "efficiency_pct", upper=100)
        msg = str(ctx.exception)
        self.assertIn("efficiency_pct", msg)
        self.assertIn("100", msg)


# ===================================================================
# FactoryEntity tests
# ===================================================================

class TestFactoryEntity(unittest.TestCase):
    """Tests for the abstract FactoryEntity base class."""

    def test_valid_creation(self) -> None:
        e = FactoryEntity("Test")
        self.assertEqual(e.name, "Test")

    def test_empty_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            FactoryEntity("")

    def test_non_string_name_raises(self) -> None:
        with self.assertRaises(TypeError):
            FactoryEntity(123)  # type: ignore[arg-type]

    def test_to_dict_raises(self) -> None:
        e = FactoryEntity("X")
        with self.assertRaises(NotImplementedError):
            e.to_dict()

    def test_from_dict_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            FactoryEntity.from_dict({})

    def test_repr(self) -> None:
        e = FactoryEntity("Widget")
        self.assertIn("Widget", repr(e))
        self.assertIn("FactoryEntity", repr(e))


# ===================================================================
# Product – valid creation
# ===================================================================

class TestProductCreation(unittest.TestCase):
    """Tests for valid Product construction."""

    def test_default_priority(self) -> None:
        p = Product("P-A", "Bracket", 30.0)
        self.assertEqual(p.product_code, "P-A")
        self.assertEqual(p.name, "Bracket")
        self.assertEqual(p.processing_time_sec, 30.0)
        self.assertEqual(p.priority, 3)

    def test_custom_priority(self) -> None:
        p = Product("P-B", "Shaft", 45.0, priority=1)
        self.assertEqual(p.priority, 1)

    def test_priority_boundaries(self) -> None:
        for prio in (1, 2, 3, 4, 5):
            p = Product("P-X", "X", 10.0, priority=prio)
            self.assertEqual(p.priority, prio)

    def test_inherits_factory_entity(self) -> None:
        p = Product("P-A", "Bracket", 30.0)
        self.assertIsInstance(p, FactoryEntity)

    def test_repr_readable(self) -> None:
        p = Product("P-A", "Bracket", 30.0, 1)
        r = repr(p)
        self.assertIn("Product", r)
        self.assertIn("P-A", r)
        self.assertIn("Bracket", r)


# ===================================================================
# Product – invalid creation (WORD Bölüm 7.4)
# ===================================================================

class TestProductInvalid(unittest.TestCase):
    """Tests for invalid Product construction – all should raise errors."""

    def test_processing_time_zero(self) -> None:
        """processing_time_sec == 0 must raise ValueError."""
        with self.assertRaises((ValueError, TypeError)):
            Product("P-A", "Bracket", 0)

    def test_processing_time_negative(self) -> None:
        """Negative processing_time_sec must raise ValueError."""
        with self.assertRaises((ValueError, TypeError)):
            Product("P-A", "Bracket", -5.0)

    def test_priority_zero(self) -> None:
        """priority == 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            Product("P-A", "Bracket", 30.0, priority=0)

    def test_priority_six(self) -> None:
        """priority == 6 must raise ValueError."""
        with self.assertRaises(ValueError):
            Product("P-A", "Bracket", 30.0, priority=6)

    def test_priority_float(self) -> None:
        """priority == 2.5 (float) must raise TypeError."""
        with self.assertRaises(TypeError):
            Product("P-A", "Bracket", 30.0, priority=2.5)  # type: ignore[arg-type]

    def test_priority_bool(self) -> None:
        """priority == True (bool) must raise TypeError."""
        with self.assertRaises(TypeError):
            Product("P-A", "Bracket", 30.0, priority=True)  # type: ignore[arg-type]

    def test_empty_product_code(self) -> None:
        """Empty product_code must raise ValueError."""
        with self.assertRaises(ValueError):
            Product("", "Bracket", 30.0)

    def test_whitespace_product_code(self) -> None:
        """Whitespace-only product_code must raise ValueError."""
        with self.assertRaises(ValueError):
            Product("   ", "Bracket", 30.0)

    def test_non_string_product_code(self) -> None:
        """Non-string product_code must raise TypeError."""
        with self.assertRaises(TypeError):
            Product(123, "Bracket", 30.0)  # type: ignore[arg-type]

    def test_empty_name(self) -> None:
        """Empty name must raise ValueError."""
        with self.assertRaises(ValueError):
            Product("P-A", "", 30.0)

    def test_processing_time_string(self) -> None:
        """String processing_time_sec must raise TypeError."""
        with self.assertRaises(TypeError):
            Product("P-A", "Bracket", "abc")  # type: ignore[arg-type]


# ===================================================================
# Product – to_dict / from_dict round-trip
# ===================================================================

class TestProductSerialization(unittest.TestCase):
    """Tests for Product to_dict and from_dict."""

    def setUp(self) -> None:
        self.product = Product("P-A", "Bracket", 30.0, priority=1)

    def test_to_dict_keys(self) -> None:
        """to_dict keys must match the data contract (section 3.4)."""
        d = self.product.to_dict()
        expected_keys = {"product_code", "name", "processing_time_sec", "priority"}
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values(self) -> None:
        d = self.product.to_dict()
        self.assertEqual(d["product_code"], "P-A")
        self.assertEqual(d["name"], "Bracket")
        self.assertEqual(d["processing_time_sec"], 30.0)
        self.assertEqual(d["priority"], 1)

    def test_round_trip(self) -> None:
        """from_dict(to_dict()) must produce an equal Product."""
        d = self.product.to_dict()
        restored = Product.from_dict(d)
        self.assertEqual(restored.product_code, self.product.product_code)
        self.assertEqual(restored.name, self.product.name)
        self.assertEqual(
            restored.processing_time_sec, self.product.processing_time_sec
        )
        self.assertEqual(restored.priority, self.product.priority)

    def test_from_dict_missing_field(self) -> None:
        """from_dict with a missing key must raise ValueError."""
        incomplete = {"product_code": "P-A", "name": "Bracket"}
        with self.assertRaises(ValueError) as ctx:
            Product.from_dict(incomplete)
        self.assertIn("Eksik alan", str(ctx.exception))

    def test_from_dict_missing_product_code(self) -> None:
        """from_dict without product_code must raise ValueError."""
        data = {"name": "Bracket", "processing_time_sec": 30.0, "priority": 1}
        with self.assertRaises(ValueError) as ctx:
            Product.from_dict(data)
        self.assertIn("product_code", str(ctx.exception))

    def test_from_dict_all_three_products(self) -> None:
        """Round-trip for each of the 3 sample products."""
        samples = [
            {"product_code": "P-A", "name": "Bracket", "processing_time_sec": 30.0, "priority": 1},
            {"product_code": "P-B", "name": "Shaft", "processing_time_sec": 45.0, "priority": 2},
            {"product_code": "P-C", "name": "Housing", "processing_time_sec": 60.0, "priority": 3},
        ]
        for data in samples:
            p = Product.from_dict(data)
            self.assertEqual(p.to_dict(), data)


# ===================================================================
# Run
# ===================================================================

if __name__ == "__main__":
    unittest.main()
