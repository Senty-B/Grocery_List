from decimal import Decimal

import pytest

from app.common.validators import (
    normalize_text,
    validate_admin_password,
    validate_household_name,
    validate_item_name,
    validate_note,
    validate_password,
    validate_quantity,
    validate_unit,
    validate_username,
)


def test_normalize_text_collapses_whitespace_and_lowercases():
    assert normalize_text("  Hello   World  ") == "hello world"


def test_normalize_text_returns_empty_string_for_none():
    assert normalize_text(None) == ""


def test_normalize_text_normalizes_unicode_compatibility_characters():
    assert normalize_text("Ｍｉｌｋ") == "milk"


def test_validate_item_name_accepts_valid_name():
    assert validate_item_name("Crème fraîche 2") == "Crème fraîche 2"


def test_validate_item_name_rejects_empty_value():
    with pytest.raises(ValueError, match="Item name is required."):
        validate_item_name("")


def test_validate_item_name_rejects_too_long_value():
    with pytest.raises(ValueError, match="100 characters or fewer"):
        validate_item_name("x" * 101)


def test_validate_item_name_rejects_invalid_characters():
    with pytest.raises(ValueError, match="invalid characters"):
        validate_item_name("<script>")


def test_validate_quantity_accepts_decimal_strings():
    assert validate_quantity("2.5") == Decimal("2.5")


def test_validate_quantity_rejects_zero():
    with pytest.raises(ValueError, match="greater than zero"):
        validate_quantity(0)


def test_validate_quantity_rejects_negative_value():
    with pytest.raises(ValueError, match="greater than zero"):
        validate_quantity(-1)


def test_validate_quantity_rejects_non_numeric_value():
    with pytest.raises(ValueError, match="valid number"):
        validate_quantity("abc")


def test_validate_unit_enforces_length_limit():
    with pytest.raises(ValueError, match="20 characters or fewer"):
        validate_unit("x" * 21)


def test_validate_note_enforces_length_limit():
    with pytest.raises(ValueError, match="255 characters or fewer"):
        validate_note("x" * 256)


def test_validate_username_accepts_underscores():
    assert validate_username("house_user_1") == "house_user_1"


def test_validate_username_rejects_short_values():
    with pytest.raises(ValueError, match="at least 3 characters"):
        validate_username("ab")


def test_validate_username_rejects_invalid_characters():
    with pytest.raises(ValueError, match="letters, numbers, and underscores"):
        validate_username("bad-user")


def test_validate_password_requires_minimum_length():
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password("short")


def test_validate_household_name_accepts_normal_values():
    assert validate_household_name("Smith Family") == "Smith Family"


def test_validate_household_name_rejects_empty_values():
    with pytest.raises(ValueError, match="Household name is required."):
        validate_household_name("  ")


def test_validate_admin_password_requires_sixteen_chars():
    with pytest.raises(ValueError, match="at least 16"):
        validate_admin_password("short-password")


def test_validate_admin_password_accepts_long_passphrase():
    passphrase = "correcthorsebatterystaple"
    assert validate_admin_password(passphrase) == passphrase
