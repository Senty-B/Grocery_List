import unittest
from decimal import Decimal

from app.common.validators import (
    normalize_text,
    validate_item_name,
    validate_note,
    validate_password,
    validate_quantity,
    validate_unit,
    validate_username,
)


class CommonValidatorsTestCase(unittest.TestCase):
    def test_normalize_text_collapses_whitespace_and_lowercases(self):
        self.assertEqual(normalize_text("  Hello   World  "), "hello world")

    def test_normalize_text_returns_empty_string_for_none(self):
        self.assertEqual(normalize_text(None), "")

    def test_validate_item_name_rejects_empty_values(self):
        with self.assertRaisesRegex(ValueError, "Item name is required."):
            validate_item_name("")

    def test_validate_item_name_accepts_plain_names(self):
        self.assertEqual(validate_item_name("Milk"), "Milk")

    def test_validate_item_name_accepts_accents_and_common_punctuation(self):
        self.assertEqual(validate_item_name("Crème fraîche, 2"), "Crème fraîche, 2")

    def test_validate_item_name_rejects_invalid_characters(self):
        with self.assertRaisesRegex(ValueError, "Item name contains invalid characters."):
            validate_item_name("<script>")

    def test_validate_quantity_rejects_negative_values(self):
        with self.assertRaisesRegex(ValueError, "Quantity must be greater than zero."):
            validate_quantity(-1)

    def test_validate_quantity_accepts_decimal_strings(self):
        self.assertEqual(validate_quantity("2.5"), Decimal("2.5"))

    def test_validate_quantity_rejects_non_numeric_values(self):
        with self.assertRaisesRegex(ValueError, "Quantity must be a valid number."):
            validate_quantity("abc")

    def test_validate_unit_returns_none_for_blank_values(self):
        self.assertIsNone(validate_unit("   "))

    def test_validate_unit_rejects_values_that_are_too_long(self):
        with self.assertRaisesRegex(ValueError, "Unit must be 20 characters or fewer."):
            validate_unit("x" * 21)

    def test_validate_note_returns_none_for_blank_values(self):
        self.assertIsNone(validate_note(""))

    def test_validate_note_rejects_values_that_are_too_long(self):
        with self.assertRaisesRegex(ValueError, "Note must be 255 characters or fewer."):
            validate_note("x" * 256)

    def test_validate_username_rejects_short_values(self):
        with self.assertRaisesRegex(
            ValueError, "Username must be at least 3 characters."
        ):
            validate_username("ab")

    def test_validate_username_accepts_underscored_names(self):
        self.assertEqual(validate_username("house_user_1"), "house_user_1")

    def test_validate_password_rejects_short_values(self):
        with self.assertRaisesRegex(ValueError, "Password must be at least 8 characters."):
            validate_password("short")

    def test_validate_password_accepts_long_enough_values(self):
        self.assertEqual(
            validate_password("long-enough-password"),
            "long-enough-password",
        )
