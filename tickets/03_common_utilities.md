# Ticket 3: Common Utilities — Validators, Authorization & Exceptions

**Phase:** 1 — Foundation  
**Priority:** Critical  
**Dependencies:** Ticket 2  
**Estimated effort:** Small–Medium

---

## Why This Matters

Every backend module (auth, grocery, favorites, household) needs shared validation logic, authorization decorators, and consistent error handling. Building these once in `app/common/` avoids code duplication and ensures rules are applied uniformly.

---

## Tasks

### 1. Create custom exception classes

`app/common/exceptions.py`:

```python
class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message="An error occurred", status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppException):
    def __init__(self, message="Validation failed"):
        super().__init__(message, status_code=400)


class AuthorizationError(AppException):
    def __init__(self, message="Not authorized"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    def __init__(self, message="Resource not found"):
        super().__init__(message, status_code=404)
```

**What these do:** When something goes wrong (bad input, user not allowed, item not found), you raise one of these instead of returning random error strings. The error handler in the app factory can then catch them and show the right page or message.

### 2. Create input validators

`app/common/validators.py`:

```python
import re
import unicodedata


def normalize_text(value):
    """Lowercase, strip whitespace, collapse repeated spaces.
    Returns empty string for None."""
    if not value:
        return ""
    text = value.strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def validate_item_name(name):
    """Item name: required, 1-100 chars, allows letters, numbers, spaces,
    hyphens, apostrophes, accents, umlauts."""
    if not name or not name.strip():
        raise ValueError("Item name is required.")
    name = name.strip()
    if len(name) > 100:
        raise ValueError("Item name must be 100 characters or fewer.")
    ALLOWED_PATTERN = re.compile(
        r"^[\w\s\-'.,&öäüéèêàáâãçñ]+$", re.UNICODE | re.IGNORECASE
    )
    if not ALLOWED_PATTERN.match(name):
        raise ValueError("Item name contains invalid characters.")
    return name


def validate_quantity(value):
    """Quantity must be a positive number. Returns Decimal."""
    from decimal import Decimal, InvalidOperation
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Quantity must be a valid number.")
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if qty > 9999:
        raise ValueError("Quantity is too large.")
    return qty


def validate_unit(unit):
    """Optional, max 20 chars."""
    if not unit:
        return None
    unit = unit.strip()
    if len(unit) > 20:
        raise ValueError("Unit must be 20 characters or fewer.")
    return unit


def validate_note(note):
    """Optional, max 255 chars."""
    if not note:
        return None
    note = note.strip()
    if len(note) > 255:
        raise ValueError("Note must be 255 characters or fewer.")
    return note


def validate_username(username):
    """Required, 3-50 chars, alphanumeric + underscores."""
    if not username or not username.strip():
        raise ValueError("Username is required.")
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if len(username) > 50:
        raise ValueError("Username must be 50 characters or fewer.")
    if not re.match(r"^[\w]+$", username, re.UNICODE):
        raise ValueError("Username may only contain letters, numbers, and underscores.")
    return username


def validate_password(password):
    """Min 8 chars."""
    if not password:
        raise ValueError("Password is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    return password
```

### 3. Create authorization decorators

`app/common/authz.py`:

```python
from functools import wraps
from flask import abort, redirect, url_for
from flask_login import current_user


def require_household(f):
    """Ensure the logged-in user belongs to a household."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.household_id:
            return redirect(url_for("household.setup"))
        return f(*args, **kwargs)
    return decorated


def require_owner(f):
    """Ensure the logged-in user is a household owner."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role != "owner":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def require_active_user(f):
    """Ensure the logged-in user account is active."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_active:
            abort(403)
        return f(*args, **kwargs)
    return decorated
```

**What is a decorator?** It's a function that wraps another function to add behavior. When you write `@require_household` above a route, Flask will first run the household check before running the route. If the check fails, the user gets redirected.

### 4. Create utility helpers

`app/common/utils.py`:

```python
import secrets
import logging
from app.extensions import db
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def generate_invite_code(length=8):
    """Generate a cryptographically secure invite code (uppercase alphanumeric)."""
    return secrets.token_hex(length // 2).upper()[:length]


def log_activity(household_id, user_id, action_type, entity_type, entity_id, payload=None):
    """Write an entry to the activity log table."""
    try:
        entry = ActivityLog(
            household_id=household_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        logger.exception("Failed to write activity log")
        db.session.rollback()
```

### 5. Register the exception handler in the app factory

In `app/__init__.py`, update `_register_error_handlers` to catch `AppException`:

```python
def _register_error_handlers(app):
    from app.common.exceptions import AppException

    @app.errorhandler(AppException)
    def handle_app_exception(e):
        return e.message, e.status_code

    @app.errorhandler(404)
    def not_found(e):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(e):
        return "Internal server error", 500
```

---

## Acceptance Criteria

- [ ] `normalize_text("  Hello   World  ")` returns `"hello world"`
- [ ] `normalize_text(None)` returns `""`
- [ ] `validate_item_name("")` raises `ValueError`
- [ ] `validate_item_name("Milk")` returns `"Milk"` (no error)
- [ ] `validate_quantity(-1)` raises `ValueError`
- [ ] `validate_quantity("2.5")` returns `Decimal("2.5")`
- [ ] `@require_household` redirects an unauthenticated user to `/login`
- [ ] `generate_invite_code()` returns a string of the expected length
- [ ] All validator edge cases are covered by unit tests
