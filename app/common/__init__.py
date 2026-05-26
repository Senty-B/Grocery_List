"""Common application helpers package."""

from app.common.authz import (
    require_active_user,
    require_admin,
    require_household,
    require_owner,
)
from app.common.exceptions import (
    AppException,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from app.common.utils import log_activity
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

__all__ = [
    "AppException",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "log_activity",
    "normalize_text",
    "require_active_user",
    "require_admin",
    "require_household",
    "require_owner",
    "validate_admin_password",
    "validate_household_name",
    "validate_item_name",
    "validate_note",
    "validate_password",
    "validate_quantity",
    "validate_unit",
    "validate_username",
]
