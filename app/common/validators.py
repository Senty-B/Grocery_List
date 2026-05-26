import re
import unicodedata
from decimal import Decimal, InvalidOperation


USERNAME_PATTERN = re.compile(r"^[\w]+$", re.UNICODE)


def normalize_text(value):
    """Lowercase, strip whitespace, and collapse repeated spaces."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).lower()


def _contains_control_characters(value):
    return any(unicodedata.category(char).startswith("C") for char in value)


def validate_item_name(name):
    """Validate grocery item names while allowing common household inputs."""
    if not name or not str(name).strip():
        raise ValueError("Item name is required.")

    name = unicodedata.normalize("NFKC", str(name)).strip()
    if len(name) > 100:
        raise ValueError("Item name must be 100 characters or fewer.")
    if _contains_control_characters(name):
        raise ValueError("Item name contains invalid characters.")

    allowed_punctuation = {" ", "-", "'", ".", ",", "&"}
    for char in name:
        if char.isalnum() or char in allowed_punctuation:
            continue
        raise ValueError("Item name contains invalid characters.")

    return name


def validate_quantity(value):
    """Quantity must be a positive decimal number."""
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Quantity must be a valid number.") from error

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if quantity > Decimal("9999"):
        raise ValueError("Quantity is too large.")

    return quantity


def validate_unit(unit):
    """Validate optional unit text."""
    if not unit:
        return None

    unit = unicodedata.normalize("NFKC", str(unit)).strip()
    if not unit:
        return None
    if len(unit) > 20:
        raise ValueError("Unit must be 20 characters or fewer.")
    if _contains_control_characters(unit):
        raise ValueError("Unit contains invalid characters.")

    return unit


def validate_note(note):
    """Validate optional note text."""
    if not note:
        return None

    note = unicodedata.normalize("NFKC", str(note)).strip()
    if not note:
        return None
    if len(note) > 255:
        raise ValueError("Note must be 255 characters or fewer.")
    if _contains_control_characters(note):
        raise ValueError("Note contains invalid characters.")

    return note


def validate_username(username):
    """Validate local usernames."""
    if not username or not str(username).strip():
        raise ValueError("Username is required.")

    username = unicodedata.normalize("NFKC", str(username)).strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if len(username) > 50:
        raise ValueError("Username must be 50 characters or fewer.")
    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username may only contain letters, numbers, and underscores."
        )

    return username


def validate_password(password):
    """Validate password length for local auth."""
    if not password:
        raise ValueError("Password is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    return password


def validate_admin_password(password):
    """Admin accounts require a noticeably stronger password."""
    if not password:
        raise ValueError("Password is required.")
    if len(password) < 16:
        raise ValueError("Admin password must be at least 16 characters.")
    if _contains_control_characters(password):
        raise ValueError("Admin password contains invalid characters.")

    return password


def validate_household_name(household_name):
    """Validate household display names."""
    if not household_name or not str(household_name).strip():
        raise ValueError("Household name is required.")

    household_name = unicodedata.normalize("NFKC", str(household_name)).strip()
    if len(household_name) > 100:
        raise ValueError("Household name must be 100 characters or fewer.")
    if _contains_control_characters(household_name):
        raise ValueError("Household name contains invalid characters.")

    return household_name
