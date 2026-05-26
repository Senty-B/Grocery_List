# Implementation Tickets — Shared Household Grocery App v1

> **Status:** Ready for implementation  
> **Total Tickets:** 16  
> **Canonical References:**  
> - Product scope: `PRD Shared Household Grocery App.md`  
> - Architecture: `Technical Architecture.md`  
> - Routes: `Route_Contract.md`  
> - Duplicate merge: `Concurrency_Duplicate_Merge_Design.md`  
> - Schema / API / UI specs: `Schema_API_UI_sub_specs.md`  
> - Deployment: `Production_Cutover_Runbook.md`, `Hostinger_Deployment_Reference.md`

---

## How to Read These Tickets

Each ticket is self-contained. Read it top to bottom. Complete every task in the order listed unless stated otherwise. When you are done, run through the **Acceptance Criteria** checklist at the bottom of the ticket — every item must pass before the ticket is considered done.

**Key rules for all tickets:**

1. Never commit secrets (`.env`, passwords) to git.
2. All code must be concise, readable, and use declarative variable naming.
3. Follow the file/folder structure exactly as specified.
4. If a ticket says "see Reference," open that file in the workspace and follow what it says.
5. Ask questions **before** guessing. If something is ambiguous, flag it.

---

## Phase Overview

| Phase | Focus | Tickets |
|-------|-------|---------|
| **Phase 1** | Foundation | 1 – 3 |
| **Phase 2** | Core Backend | 4 – 8 |
| **Phase 3** | Frontend & UI | 9 – 11 |
| **Phase 4** | DevOps & Deployment | 12 – 14 |
| **Phase 5** | Hardening & Polish | 15 – 16 |

**Critical path:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 12 → 15

---
---

## PHASE 1: FOUNDATION

---

### Ticket 1: Project Structure & App Factory Setup

**Priority:** Critical  
**Dependencies:** None  
**Estimated effort:** Small

#### Why This Matters

Every other ticket depends on this one. We are setting up the Flask application skeleton using the **app factory pattern**. This pattern means the app is created by a function (`create_app`) rather than as a global variable, which makes testing and configuration switching possible.

#### What You Will Build

A runnable Flask project with the correct folder structure, configuration for three environments (development, testing, production), and lazy-loaded extensions.

#### Tasks

**1. Create the project root files**

Create these files at the repository root:

`requirements.txt` — pin the core dependencies:

```text
Flask>=3.1,<4
Flask-Login>=0.6,<1
Flask-WTF>=1.2,<2
SQLAlchemy>=2.0,<3
Flask-SQLAlchemy>=3.1,<4
alembic>=1.13,<2
Flask-Migrate>=4.0,<5
psycopg[binary]>=3.1,<4
bcrypt>=4.1,<5
gunicorn>=22.0,<23
python-dotenv>=1.0,<2
```

`.flaskenv` — tells `flask run` which file to use:

```text
FLASK_APP=wsgi.py
FLASK_DEBUG=1
```

`.env.example` — template for local development secrets:

```text
SECRET_KEY=dev-secret-change-me
DATABASE_URL=postgresql+psycopg://grocery:grocery@localhost:5432/grocery_dev
LOG_LEVEL=DEBUG
```

`.gitignore` — at minimum:

```text
__pycache__/
*.pyc
.env
.env.prod
*.db
node_modules/
.venv/
```

**2. Create the `app/` package**

`app/__init__.py` — the app factory:

```python
from flask import Flask
from app.config import config_map
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    _register_blueprints(app)
    _register_error_handlers(app)

    return app


def _register_blueprints(app):
    from app.auth.routes import auth_bp
    from app.household.routes import household_bp
    from app.grocery.routes import grocery_bp
    from app.favorites.routes import favorites_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/household")
    app.register_blueprint(grocery_bp, url_prefix="/grocery")
    app.register_blueprint(favorites_bp, url_prefix="/favorites")


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(e):
        return "Internal server error", 500
```

**What's happening here:**
- `create_app()` is a function that builds a fresh Flask app every time it's called.
- `config_name` lets us switch between dev/test/prod settings.
- Extensions (database, login, CSRF, migrations) are initialized lazily — they are created once globally but attached to the app here.
- Blueprints are Flask's way of grouping related routes into modules.

`app/config.py` — environment-specific settings:

```python
import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://grocery:grocery@localhost:5432/grocery_dev",
    )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://grocery:grocery@localhost:5432/grocery_test",
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
```

`app/extensions.py` — one place for all extension instances:

```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
migrate = Migrate()
```

**Why a separate extensions file?** Extensions need to exist before the app is created (so models can import `db`), but they can't be initialized without an app. This file creates the objects; `create_app()` attaches them to the app later.

**3. Create the entry points**

`wsgi.py`:

```python
import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))
```

`run.py` (convenient local runner):

```python
from wsgi import app

if __name__ == "__main__":
    app.run()
```

**4. Create empty blueprint packages**

Create these files so the app factory can import blueprints without errors. Each file just declares the blueprint and at least one placeholder route:

- `app/auth/__init__.py` (empty)
- `app/auth/routes.py` — minimal:
  ```python
  from flask import Blueprint
  auth_bp = Blueprint("auth", __name__)

  @auth_bp.route("/login")
  def login():
      return "Login page placeholder"
  ```
- `app/household/__init__.py` (empty)
- `app/household/routes.py` — same pattern, blueprint name `household`
- `app/grocery/__init__.py` (empty)
- `app/grocery/routes.py` — same pattern, blueprint name `grocery`
- `app/favorites/__init__.py` (empty)
- `app/favorites/routes.py` — same pattern, blueprint name `favorites`
- `app/common/__init__.py` (empty)

**5. Create empty directories**

- `app/templates/` (add a `.gitkeep` file inside)
- `app/static/css/` (add a `.gitkeep` file inside)
- `app/static/js/` (add a `.gitkeep` file inside)
- `migrations/` (will be populated by Alembic in Ticket 2)
- `tests/` (add `__init__.py`)
- `docker/` (add a `.gitkeep`)

**6. Set up structured logging**

Add to `app/__init__.py` inside `create_app()`, before returning `app`:

```python
import logging
log_level = app.config.get("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

#### Acceptance Criteria

- [ ] `pip install -r requirements.txt` succeeds with no errors
- [ ] `flask run` starts the dev server without errors
- [ ] Visiting `http://localhost:5000/login` shows the placeholder text
- [ ] Visiting `http://localhost:5000/grocery` shows the placeholder text
- [ ] `create_app("testing")` returns an app with `TESTING=True`
- [ ] `.env.example` exists and contains all required env vars
- [ ] Folder structure matches the spec exactly

---

### Ticket 2: Database Setup — PostgreSQL, SQLAlchemy & Alembic

**Priority:** Critical  
**Dependencies:** Ticket 1  
**Estimated effort:** Medium

#### Why This Matters

This ticket creates all the database tables the app needs. We use SQLAlchemy (an ORM that lets us write Python classes instead of raw SQL) and Alembic (a migration tool that tracks schema changes over time so they can be applied in order).

#### Reference

- Full schema: `Schema_API_UI_sub_specs.md` sections 1.1–1.4
- Dedupe index: `Concurrency_Duplicate_Merge_Design.md` section 3

#### Tasks

**1. Make sure a local PostgreSQL database is running**

You need a Postgres instance on your machine. Create two databases:

```sql
CREATE DATABASE grocery_dev;
CREATE DATABASE grocery_test;
CREATE USER grocery WITH PASSWORD 'grocery';
GRANT ALL PRIVILEGES ON DATABASE grocery_dev TO grocery;
GRANT ALL PRIVILEGES ON DATABASE grocery_test TO grocery;
```

Alternatively, use Docker for local Postgres:

```bash
docker run -d --name grocery-pg -e POSTGRES_USER=grocery -e POSTGRES_PASSWORD=grocery -e POSTGRES_DB=grocery_dev -p 5432:5432 postgres:16-alpine
```

**2. Initialize Flask-Migrate (Alembic wrapper)**

From the project root, with your virtual environment active:

```bash
flask db init
```

This creates a `migrations/` folder with Alembic config files. Open `migrations/env.py` and make sure it imports your models so Alembic can auto-detect them. Add near the top:

```python
from app.extensions import db
target_metadata = db.metadata
```

**3. Create SQLAlchemy models**

Each model is a Python class that maps to a database table. Create these files:

`app/models/__init__.py`:

```python
from app.models.household import Household
from app.models.user import User
from app.models.grocery_item import GroceryItem
from app.models.favorite_item import FavoriteItem
from app.models.activity_log import ActivityLog
```

`app/models/household.py`:

```python
from app.extensions import db
from datetime import datetime, timezone


class Household(db.Model):
    __tablename__ = "household"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(32), nullable=False, unique=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    users = db.relationship("User", backref="household", lazy="dynamic")
    grocery_items = db.relationship("GroceryItem", backref="household", lazy="dynamic")
    favorite_items = db.relationship("FavoriteItem", backref="household", lazy="dynamic")
```

**What each column means:**
- `id` — auto-incrementing primary key, Postgres handles the counter.
- `name` — the household display name, e.g. "Smith Family".
- `invite_code` — a random string other users type to join this household.
- `created_at` — automatically set to "now" when the row is created.
- The `relationship` lines tell SQLAlchemy how to navigate between tables (e.g., `household.users` gives all users in that household).

`app/models/user.py`:

```python
from app.extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

**Key details:**
- `UserMixin` is from Flask-Login — it gives the class helper methods like `is_authenticated`.
- `household_id` is a **foreign key** pointing to `household.id`. The `ondelete="CASCADE"` means if a household is deleted, its users are deleted too.
- `role` is either `"owner"` or `"member"`.

`app/models/grocery_item.py`:

```python
from app.extensions import db
from datetime import datetime, timezone


class GroceryItem(db.Model):
    __tablename__ = "grocery_item"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    normalized_unit = db.Column(db.String(20), nullable=False, default="")
    normalized_note = db.Column(db.String(255), nullable=False, default="")
    quantity_value = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    unit = db.Column(db.String(20), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    checked_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_grocery_household_status", "household_id", "status"),
        db.Index("ix_grocery_household_normalized", "household_id", "normalized_name"),
    )
```

**Key details:**
- `normalized_name`, `normalized_unit`, `normalized_note` are lowercase/stripped versions of the display fields, used to detect duplicates.
- `status` is always `"active"` or `"checked"`.
- `__table_args__` creates composite database indexes for faster queries.

`app/models/favorite_item.py`:

```python
from app.extensions import db
from datetime import datetime, timezone


class FavoriteItem(db.Model):
    __tablename__ = "favorite_item"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    default_quantity_value = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    default_unit = db.Column(db.String(20), nullable=True)
    default_note = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_favorite_household_sort", "household_id", "sort_order"),
        db.Index("ix_favorite_household_normalized", "household_id", "normalized_name"),
    )
```

`app/models/activity_log.py`:

```python
from app.extensions import db
from datetime import datetime, timezone


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    payload_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

**4. Import models in the app factory**

In `app/__init__.py`, add this import inside `create_app()` **before** `migrate.init_app(...)`:

```python
import app.models  # noqa: F401 — ensures Alembic sees all models
```

**5. Create the active dedupe partial unique index migration**

After generating the initial migration with `flask db migrate -m "initial tables"`, you must **manually edit** the migration file to add the partial unique index. Add this inside the `upgrade()` function:

```python
op.create_index(
    "uq_grocery_active_dedupe",
    "grocery_item",
    ["household_id", "normalized_name", "normalized_unit", "normalized_note"],
    unique=True,
    postgresql_where=sa.text("status = 'active'"),
)
```

And in `downgrade()`:

```python
op.drop_index("uq_grocery_active_dedupe", table_name="grocery_item")
```

**What is a partial unique index?** It's a uniqueness constraint that only applies to rows matching a condition. Here, it means: "Within one household, there can only be one *active* item with the same normalized name + unit + note." Checked items are excluded, so the same item can appear again after it's been confirmed/deleted.

**6. Configure the Flask-Login user loader**

In `app/extensions.py` or `app/auth/__init__.py`, add:

```python
@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return db.session.get(User, int(user_id))
```

**7. Apply migrations**

```bash
flask db migrate -m "initial tables"
# Edit the generated migration to add the dedupe index (step 5)
flask db upgrade
```

Verify in psql or a DB client that all five tables exist and the partial unique index is present:

```sql
\d grocery_item
\di uq_grocery_active_dedupe
```

#### Acceptance Criteria

- [ ] `flask db upgrade` creates all 5 tables from an empty database
- [ ] `flask db downgrade base` removes all tables cleanly
- [ ] Running `flask db upgrade` a second time is a no-op (idempotent)
- [ ] The partial unique index `uq_grocery_active_dedupe` exists on `grocery_item`
- [ ] All foreign keys reference the correct parent tables
- [ ] Model relationships work: you can create a Household, add a User to it, and query `household.users`

---

### Ticket 3: Common Utilities — Validators, Authorization & Exceptions

**Priority:** Critical  
**Dependencies:** Ticket 2  
**Estimated effort:** Small–Medium

#### Why This Matters

Every backend module (auth, grocery, favorites, household) needs shared validation logic, authorization decorators, and consistent error handling. Building these once in `app/common/` avoids code duplication and ensures rules are applied uniformly.

#### Tasks

**1. Create custom exception classes**

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

**2. Create input validators**

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

**3. Create authorization decorators**

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

**4. Create utility helpers**

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

**5. Register the exception handler in the app factory**

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

#### Acceptance Criteria

- [ ] `normalize_text("  Hello   World  ")` returns `"hello world"`
- [ ] `normalize_text(None)` returns `""`
- [ ] `validate_item_name("")` raises `ValueError`
- [ ] `validate_item_name("Milk")` returns `"Milk"` (no error)
- [ ] `validate_quantity(-1)` raises `ValueError`
- [ ] `validate_quantity("2.5")` returns `Decimal("2.5")`
- [ ] `@require_household` redirects an unauthenticated user to `/login`
- [ ] `generate_invite_code()` returns a string of the expected length
- [ ] All validator edge cases are covered by unit tests

---
---

## PHASE 2: CORE BACKEND

---

### Ticket 4: Auth Module — Registration, Login & Household Creation

**Priority:** Critical  
**Dependencies:** Ticket 2, Ticket 3  
**Estimated effort:** Medium

#### Why This Matters

Users must be able to create an account, create a household, log in, log out, and join an existing household via invite code. This is the entry point of the entire app — nothing works without authentication.

#### Reference

- Routes: `Route_Contract.md` sections 3, 4
- Schema: `Schema_API_UI_sub_specs.md` sections 1.1, 1.2, 2.1

#### Tasks

**1. Create WTForms form classes**

`app/auth/forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    household_name = StringField("Household Name", validators=[DataRequired(), Length(max=100)])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class JoinHouseholdForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    invite_code = StringField("Invite Code", validators=[DataRequired(), Length(max=32)])
    submit = SubmitField("Join Household")
```

**What is WTForms?** It's a library that handles form validation on the server side. Each `Field` has `validators` that check the data. `FlaskForm` automatically includes CSRF protection.

**2. Create the auth service layer**

`app/auth/services.py`:

```python
import bcrypt
import logging
from app.extensions import db
from app.models.user import User
from app.models.household import Household
from app.common.utils import generate_invite_code, log_activity
from app.common.validators import validate_username, validate_password

logger = logging.getLogger(__name__)


def hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain_password, hashed):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))


def register_owner(username, password, household_name):
    """Create a new household and register the owner user.
    Returns the created User."""
    validate_username(username)
    validate_password(password)

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    household = Household(
        name=household_name.strip(),
        invite_code=generate_invite_code(),
    )
    db.session.add(household)
    db.session.flush()  # get household.id before creating user

    user = User(
        household_id=household.id,
        username=username.strip(),
        password_hash=hash_password(password),
        role="owner",
    )
    db.session.add(user)
    db.session.commit()

    logger.info("Registered owner '%s' for household '%s'", username, household_name)
    return user


def join_household(username, password, invite_code):
    """Register a new user and add them to an existing household via invite code.
    Returns the created User."""
    validate_username(username)
    validate_password(password)

    household = Household.query.filter_by(invite_code=invite_code.strip().upper()).first()
    if not household:
        raise ValueError("Invalid invite code.")

    active_member_count = User.query.filter_by(
        household_id=household.id, is_active=True
    ).count()
    if active_member_count >= 5:
        raise ValueError("This household has reached the maximum of 5 members.")

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    user = User(
        household_id=household.id,
        username=username.strip(),
        password_hash=hash_password(password),
        role="member",
    )
    db.session.add(user)
    db.session.commit()

    logger.info("User '%s' joined household '%s'", username, household.name)
    return user


def authenticate_user(username, password):
    """Verify credentials. Returns User if valid, None otherwise."""
    user = User.query.filter_by(username=username, is_active=True).first()
    if user and check_password(password, user.password_hash):
        return user
    return None
```

**3. Create the auth routes**

`app/auth/routes.py`:

```python
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth.forms import RegistrationForm, LoginForm, JoinHouseholdForm
from app.auth.services import register_owner, join_household, authenticate_user

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data, form.password.data)
        if user:
            login_user(user)
            logger.info("User '%s' logged in", user.username)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("grocery.index"))
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = register_owner(
                form.username.data,
                form.password.data,
                form.household_name.data,
            )
            login_user(user)
            flash("Account created! Welcome to your household.", "success")
            return redirect(url_for("grocery.index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/register/join", methods=["GET", "POST"])
def register_join():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = JoinHouseholdForm()
    if form.validate_on_submit():
        try:
            user = join_household(
                form.username.data,
                form.password.data,
                form.invite_code.data,
            )
            login_user(user)
            flash("You've joined the household!", "success")
            return redirect(url_for("grocery.index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("auth/join.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logger.info("User '%s' logged out", current_user.username)
    logout_user()
    return redirect(url_for("auth.login"))
```

**4. Create placeholder templates**

Create minimal templates so routes don't crash. Full styling is in Ticket 9/10.

- `app/templates/auth/login.html`
- `app/templates/auth/register.html`
- `app/templates/auth/join.html`

Each should extend a base template and render the form fields with CSRF token. Example for login:

```html
{% extends "base.html" %}
{% block content %}
<h1>Login</h1>
<form method="POST">
  {{ form.hidden_tag() }}
  <div>{{ form.username.label }} {{ form.username() }}</div>
  <div>{{ form.password.label }} {{ form.password() }}</div>
  <button type="submit">Log In</button>
</form>
<p>New household? <a href="{{ url_for('auth.register') }}">Register</a></p>
<p>Have an invite code? <a href="{{ url_for('auth.register_join') }}">Join</a></p>
{% endblock %}
```

Create a minimal `app/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Grocery List{% endblock %}</title>
</head>
<body>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
      <p class="{{ category }}">{{ message }}</p>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</body>
</html>
```

#### Acceptance Criteria

- [ ] A new user can register and a household is automatically created
- [ ] The registered user is the household `owner`
- [ ] An invite code is generated and stored on the household
- [ ] A second user can join using the invite code
- [ ] The 6th user trying to join a household gets a "maximum members" error
- [ ] Login with correct credentials redirects to `/grocery`
- [ ] Login with wrong credentials shows an error message
- [ ] Passwords are stored as bcrypt hashes (never plaintext)
- [ ] `POST /logout` ends the session and redirects to `/login`
- [ ] CSRF token is present and validated on all POST forms
- [ ] Username uniqueness is enforced (duplicate usernames rejected)

---

### Ticket 5: Grocery Module — Add, Toggle, Confirm & Search

**Priority:** Critical  
**Dependencies:** Ticket 4  
**Estimated effort:** Medium–Large

#### Why This Matters

This is the core feature of the entire application. Users add grocery items, check them off while shopping, and confirm purchases to clean the list. The duplicate-merge logic (UPSERT) is the most technically important part — it prevents race conditions when two users add the same item at the same time.

#### Reference

- Routes: `Route_Contract.md` section 5
- Duplicate merge: `Concurrency_Duplicate_Merge_Design.md` (full document)
- Schema: `Schema_API_UI_sub_specs.md` section 1.3

#### Tasks

**1. Create the grocery service layer**

`app/grocery/services.py`:

This is the most critical file in the app. It contains the business logic for all grocery operations.

```python
import logging
from decimal import Decimal
from sqlalchemy import text
from app.extensions import db
from app.models.grocery_item import GroceryItem
from app.models.favorite_item import FavoriteItem
from app.common.validators import (
    normalize_text, validate_item_name, validate_quantity,
    validate_unit, validate_note,
)

logger = logging.getLogger(__name__)

UPSERT_GROCERY_ITEM_SQL = text("""
    INSERT INTO grocery_item (
        household_id, name, normalized_name,
        unit, normalized_unit,
        note, normalized_note,
        quantity_value, status,
        created_by_user_id, created_at, updated_at
    ) VALUES (
        :household_id, :name, :normalized_name,
        :unit, :normalized_unit,
        :note, :normalized_note,
        :quantity_value, 'active',
        :created_by_user_id, NOW(), NOW()
    )
    ON CONFLICT (household_id, normalized_name, normalized_unit, normalized_note)
        WHERE status = 'active'
    DO UPDATE SET
        quantity_value = grocery_item.quantity_value + EXCLUDED.quantity_value,
        updated_at = NOW()
    RETURNING id, quantity_value, status
""")


def add_grocery_item(household_id, user_id, name, quantity=1, unit=None, note=None):
    """Add item or merge quantity if active duplicate exists.
    Uses a single atomic UPSERT — no race conditions."""
    name = validate_item_name(name)
    quantity = validate_quantity(quantity)
    unit = validate_unit(unit)
    note = validate_note(note)

    payload = {
        "household_id": household_id,
        "name": name,
        "normalized_name": normalize_text(name),
        "unit": unit or "",
        "normalized_unit": normalize_text(unit),
        "note": note or "",
        "normalized_note": normalize_text(note),
        "quantity_value": quantity,
        "created_by_user_id": user_id,
    }

    result = db.session.execute(UPSERT_GROCERY_ITEM_SQL, payload).mappings().one()
    db.session.commit()
    logger.info("Grocery item upserted: id=%s qty=%s", result["id"], result["quantity_value"])
    return dict(result)


def toggle_item_status(item_id, household_id, user_id):
    """Toggle a grocery item between active and checked."""
    item = GroceryItem.query.filter_by(id=item_id, household_id=household_id).first()
    if not item:
        raise ValueError("Item not found.")

    if item.status == "active":
        item.status = "checked"
        item.checked_by_user_id = user_id
        from datetime import datetime, timezone
        item.checked_at = datetime.now(timezone.utc)
    else:
        item.status = "active"
        item.checked_by_user_id = None
        item.checked_at = None

    db.session.commit()
    logger.info("Item %s toggled to '%s'", item_id, item.status)
    return item


def confirm_purchase(household_id):
    """Permanently delete all checked items for the household."""
    deleted = GroceryItem.query.filter_by(
        household_id=household_id, status="checked"
    ).delete()
    db.session.commit()
    logger.info("Confirmed purchase: %d items removed for household %s", deleted, household_id)
    return deleted


def get_grocery_list(household_id):
    """Return active items first, then checked items, each sorted alphabetically."""
    active_items = (
        GroceryItem.query
        .filter_by(household_id=household_id, status="active")
        .order_by(GroceryItem.name)
        .all()
    )
    checked_items = (
        GroceryItem.query
        .filter_by(household_id=household_id, status="checked")
        .order_by(GroceryItem.name)
        .all()
    )
    return active_items, checked_items


def search_items(household_id, query):
    """Search favorites and previously used item names for suggestions."""
    if not query or len(query.strip()) < 1:
        return []

    search_term = f"%{normalize_text(query)}%"

    favorites = (
        FavoriteItem.query
        .filter_by(household_id=household_id)
        .filter(FavoriteItem.normalized_name.ilike(search_term))
        .order_by(FavoriteItem.sort_order)
        .limit(5)
        .all()
    )

    previous_items = (
        db.session.query(GroceryItem.name)
        .filter_by(household_id=household_id)
        .filter(GroceryItem.normalized_name.ilike(search_term))
        .distinct()
        .limit(5)
        .all()
    )

    return {
        "favorites": favorites,
        "history": [row.name for row in previous_items],
    }
```

**Key concept — the UPSERT:** The `INSERT ... ON CONFLICT ... DO UPDATE` statement is a single SQL command. PostgreSQL guarantees it runs atomically — if two users submit at the same time, one will insert and the other will just add to the quantity. No duplicate rows are ever created.

**2. Create the grocery form**

`app/grocery/forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class AddItemForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired()])
    quantity = DecimalField("Quantity", default=1, validators=[NumberRange(min=0.01)])
    unit = StringField("Unit", validators=[Optional()])
    note = StringField("Note", validators=[Optional()])
    submit = SubmitField("Add")
```

**3. Create the grocery routes**

`app/grocery/routes.py`:

```python
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.common.authz import require_household
from app.grocery.forms import AddItemForm
from app.grocery.services import (
    add_grocery_item, toggle_item_status, confirm_purchase,
    get_grocery_list, search_items,
)
from app.models.favorite_item import FavoriteItem

logger = logging.getLogger(__name__)
grocery_bp = Blueprint("grocery", __name__)


def _is_htmx():
    return request.headers.get("HX-Request") == "true"


@grocery_bp.route("/")
@login_required
@require_household
def index():
    active_items, checked_items = get_grocery_list(current_user.household_id)
    favorites = (
        FavoriteItem.query
        .filter_by(household_id=current_user.household_id)
        .order_by(FavoriteItem.sort_order)
        .limit(8)
        .all()
    )
    form = AddItemForm()
    return render_template(
        "grocery/index.html",
        active_items=active_items,
        checked_items=checked_items,
        favorites=favorites,
        form=form,
    )


@grocery_bp.route("/items", methods=["POST"])
@login_required
@require_household
def add_item():
    form = AddItemForm()
    if form.validate_on_submit():
        try:
            add_grocery_item(
                household_id=current_user.household_id,
                user_id=current_user.id,
                name=form.name.data,
                quantity=form.quantity.data or 1,
                unit=form.unit.data,
                note=form.note.data,
            )
            if _is_htmx():
                active_items, checked_items = get_grocery_list(current_user.household_id)
                return render_template(
                    "grocery/_list.html",
                    active_items=active_items,
                    checked_items=checked_items,
                )
            flash("Item added!", "success")
        except ValueError as e:
            flash(str(e), "error")
    return redirect(url_for("grocery.index"))


@grocery_bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@login_required
@require_household
def toggle(item_id):
    try:
        item = toggle_item_status(item_id, current_user.household_id, current_user.id)
        if _is_htmx():
            return render_template("grocery/_item_row.html", item=item)
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("grocery.index"))


@grocery_bp.route("/confirm", methods=["POST"])
@login_required
@require_household
def confirm():
    count = confirm_purchase(current_user.household_id)
    if _is_htmx():
        return render_template("grocery/_checked_list.html", checked_items=[])
    flash(f"{count} item(s) removed.", "success")
    return redirect(url_for("grocery.index"))


@grocery_bp.route("/search")
@login_required
@require_household
def search():
    query = request.args.get("q", "")
    results = search_items(current_user.household_id, query)
    return render_template("grocery/_search_results.html", results=results)


@grocery_bp.route("/fragments/list")
@login_required
@require_household
def fragment_list():
    active_items, checked_items = get_grocery_list(current_user.household_id)
    return render_template(
        "grocery/_list.html",
        active_items=active_items,
        checked_items=checked_items,
    )
```

**4. Create placeholder templates**

Create these minimal templates (full styling in Ticket 10):

- `app/templates/grocery/index.html` — main page
- `app/templates/grocery/_list.html` — HTMX fragment for the full list
- `app/templates/grocery/_item_row.html` — single item row fragment
- `app/templates/grocery/_checked_list.html` — checked items section
- `app/templates/grocery/_search_results.html` — search dropdown

#### Acceptance Criteria

- [ ] Adding an item with name "Milk" creates one active `GroceryItem`
- [ ] Adding "Milk" again increments the existing item's quantity (not a new row)
- [ ] Two simultaneous adds of the same item result in one row with summed quantity
- [ ] Toggling an active item sets status to `"checked"` and records `checked_by_user_id`
- [ ] Toggling a checked item sets status back to `"active"` and clears check fields
- [ ] Confirm purchase deletes **only** checked items (active items remain)
- [ ] Search returns matching favorites and historical item names
- [ ] All routes require authentication (redirect to `/login` if not logged in)
- [ ] A user cannot access items from another household
- [ ] HTMX requests return HTML fragments; non-HTMX requests redirect

---

### Ticket 6: Favorites Module — Quick-Add & Management

**Priority:** High  
**Dependencies:** Ticket 5  
**Estimated effort:** Medium

#### Why This Matters

Favorites let users save commonly bought items for one-tap adding. The first 8 favorites appear on the grocery page as quick-add buttons, reducing friction for daily use.

#### Reference

- Routes: `Route_Contract.md` section 6
- Schema: `Schema_API_UI_sub_specs.md` section 1.4

#### Tasks

**1. Create the favorites service layer**

`app/favorites/services.py`:

```python
import logging
from app.extensions import db
from app.models.favorite_item import FavoriteItem
from app.common.validators import (
    normalize_text, validate_item_name, validate_quantity,
    validate_unit, validate_note,
)
from app.grocery.services import add_grocery_item

logger = logging.getLogger(__name__)


def add_favorite(household_id, name, quantity=1, unit=None, note=None):
    """Add a new favorite to the household."""
    name = validate_item_name(name)
    quantity = validate_quantity(quantity)
    unit = validate_unit(unit)
    note = validate_note(note)

    normalized = normalize_text(name)
    existing = FavoriteItem.query.filter_by(
        household_id=household_id, normalized_name=normalized
    ).first()
    if existing:
        raise ValueError("This item is already a favorite.")

    max_order = (
        db.session.query(db.func.max(FavoriteItem.sort_order))
        .filter_by(household_id=household_id)
        .scalar()
    ) or 0

    favorite = FavoriteItem(
        household_id=household_id,
        name=name,
        normalized_name=normalized,
        default_quantity_value=quantity,
        default_unit=unit,
        default_note=note,
        sort_order=max_order + 1,
    )
    db.session.add(favorite)
    db.session.commit()
    logger.info("Favorite added: '%s' for household %s", name, household_id)
    return favorite


def remove_favorite(favorite_id, household_id):
    """Delete a favorite."""
    favorite = FavoriteItem.query.filter_by(
        id=favorite_id, household_id=household_id
    ).first()
    if not favorite:
        raise ValueError("Favorite not found.")

    db.session.delete(favorite)
    db.session.commit()
    logger.info("Favorite %s removed", favorite_id)


def reorder_favorite(favorite_id, household_id, new_position):
    """Change a favorite's sort order."""
    favorite = FavoriteItem.query.filter_by(
        id=favorite_id, household_id=household_id
    ).first()
    if not favorite:
        raise ValueError("Favorite not found.")

    favorite.sort_order = new_position
    db.session.commit()


def quick_add_from_favorite(favorite_id, household_id, user_id, quantity_override=None):
    """Add a grocery item using the favorite's defaults."""
    favorite = FavoriteItem.query.filter_by(
        id=favorite_id, household_id=household_id
    ).first()
    if not favorite:
        raise ValueError("Favorite not found.")

    quantity = quantity_override or favorite.default_quantity_value
    return add_grocery_item(
        household_id=household_id,
        user_id=user_id,
        name=favorite.name,
        quantity=quantity,
        unit=favorite.default_unit,
        note=favorite.default_note,
    )


def get_favorites_list(household_id):
    """Return all favorites for a household, ordered by sort_order."""
    return (
        FavoriteItem.query
        .filter_by(household_id=household_id)
        .order_by(FavoriteItem.sort_order)
        .all()
    )
```

**2. Create the favorites form**

`app/favorites/forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class AddFavoriteForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired()])
    quantity = DecimalField("Default Quantity", default=1, validators=[NumberRange(min=0.01)])
    unit = StringField("Default Unit", validators=[Optional()])
    note = StringField("Default Note", validators=[Optional()])
    submit = SubmitField("Add to Favorites")
```

**3. Create the favorites routes**

`app/favorites/routes.py`:

```python
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.common.authz import require_household
from app.favorites.forms import AddFavoriteForm
from app.favorites.services import (
    add_favorite, remove_favorite, reorder_favorite,
    quick_add_from_favorite, get_favorites_list,
)

logger = logging.getLogger(__name__)
favorites_bp = Blueprint("favorites", __name__)


def _is_htmx():
    return request.headers.get("HX-Request") == "true"


@favorites_bp.route("/")
@login_required
@require_household
def index():
    favorites = get_favorites_list(current_user.household_id)
    form = AddFavoriteForm()
    return render_template("favorites/index.html", favorites=favorites, form=form)


@favorites_bp.route("/", methods=["POST"])
@login_required
@require_household
def create():
    form = AddFavoriteForm()
    if form.validate_on_submit():
        try:
            add_favorite(
                household_id=current_user.household_id,
                name=form.name.data,
                quantity=form.quantity.data or 1,
                unit=form.unit.data,
                note=form.note.data,
            )
            if _is_htmx():
                favorites = get_favorites_list(current_user.household_id)
                return render_template("favorites/_list.html", favorites=favorites)
            flash("Favorite added!", "success")
        except ValueError as e:
            flash(str(e), "error")
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/delete", methods=["POST"])
@login_required
@require_household
def delete(favorite_id):
    try:
        remove_favorite(favorite_id, current_user.household_id)
        if _is_htmx():
            return "", 200
        flash("Favorite removed.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/reorder", methods=["POST"])
@login_required
@require_household
def reorder(favorite_id):
    new_position = request.form.get("position", type=int)
    if new_position is None:
        flash("Invalid position.", "error")
        return redirect(url_for("favorites.index"))
    try:
        reorder_favorite(favorite_id, current_user.household_id, new_position)
        if _is_htmx():
            favorites = get_favorites_list(current_user.household_id)
            return render_template("favorites/_list.html", favorites=favorites)
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/quick-add", methods=["POST"])
@login_required
@require_household
def quick_add(favorite_id):
    try:
        quick_add_from_favorite(
            favorite_id=favorite_id,
            household_id=current_user.household_id,
            user_id=current_user.id,
        )
        if _is_htmx():
            return render_template("favorites/_quick_add_feedback.html", success=True)
        flash("Item added from favorite!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("grocery.index"))
```

**4. Create placeholder templates**

- `app/templates/favorites/index.html`
- `app/templates/favorites/_list.html`
- `app/templates/favorites/_quick_add_feedback.html`

#### Acceptance Criteria

- [ ] A user can add an item to favorites
- [ ] Duplicate favorite names (same household) are rejected
- [ ] Favorites are returned ordered by `sort_order`
- [ ] Deleting a favorite removes it from the database
- [ ] Quick-add creates a grocery item using the favorite's defaults
- [ ] Quick-add uses the same UPSERT logic (merges if duplicate active item exists)
- [ ] Reorder changes the `sort_order` value
- [ ] All routes are protected by `@login_required` and `@require_household`
- [ ] A user cannot access another household's favorites

---

### Ticket 7: Household Module — Invite Codes & Member Management

**Priority:** High  
**Dependencies:** Ticket 4  
**Estimated effort:** Small

#### Why This Matters

The household owner needs to see their invite code to share it, rotate it if needed, and view who is in the household.

#### Reference

- Routes: `Route_Contract.md` section 4

#### Tasks

**1. Create the household service layer**

`app/household/services.py`:

```python
import logging
from app.extensions import db
from app.models.household import Household
from app.models.user import User
from app.common.utils import generate_invite_code

logger = logging.getLogger(__name__)


def get_household_info(household_id):
    """Return the household and its members."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")
    members = User.query.filter_by(household_id=household_id, is_active=True).all()
    return household, members


def rotate_invite_code(household_id):
    """Generate a new invite code for the household."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")
    household.invite_code = generate_invite_code()
    db.session.commit()
    logger.info("Invite code rotated for household %s", household_id)
    return household.invite_code
```

**2. Create the household routes**

`app/household/routes.py`:

```python
import logging
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.common.authz import require_household, require_owner
from app.household.services import get_household_info, rotate_invite_code

logger = logging.getLogger(__name__)
household_bp = Blueprint("household", __name__)


@household_bp.route("/")
@login_required
@require_household
def index():
    household, members = get_household_info(current_user.household_id)
    return render_template(
        "household/index.html",
        household=household,
        members=members,
        is_owner=current_user.role == "owner",
    )


@household_bp.route("/rotate-code", methods=["POST"])
@login_required
@require_owner
def rotate_code():
    new_code = rotate_invite_code(current_user.household_id)
    flash(f"New invite code: {new_code}", "success")
    return redirect(url_for("household.index"))
```

**3. Create placeholder template**

`app/templates/household/index.html` — shows household name, invite code (if owner), member list.

#### Acceptance Criteria

- [ ] Owner can view the household page with invite code visible
- [ ] Members can view the household page but cannot see invite code (or it's view-only)
- [ ] Owner can rotate the invite code, and old code stops working
- [ ] Member list shows all active members with their roles
- [ ] `@require_owner` blocks members from accessing `/household/rotate-code`

---

### Ticket 8: Testing — Unit & Integration Tests

**Priority:** High  
**Dependencies:** Tickets 5, 6, 7  
**Estimated effort:** Medium–Large

#### Why This Matters

Tests prove the app works correctly and prevent future changes from breaking existing behavior. Without tests, you're flying blind.

#### Tasks

**1. Set up the test infrastructure**

`tests/conftest.py`:

```python
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(app, db):
    """Returns a test client logged in as a household owner."""
    from app.auth.services import register_owner
    with app.app_context():
        user = register_owner("testowner", "password123", "Test Household")
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            yield c, user
```

**2. Write unit tests for validators**

`tests/test_validators.py` — test every function in `app/common/validators.py`:

- `normalize_text` with whitespace, None, Unicode
- `validate_item_name` with valid names, empty, too long, special chars
- `validate_quantity` with valid numbers, zero, negative, non-numeric
- `validate_unit` and `validate_note` length limits
- `validate_username` and `validate_password` edge cases

**3. Write unit tests for grocery services**

`tests/test_grocery_services.py`:

- Adding a new item creates one row
- Adding the same item twice increments quantity (UPSERT test)
- Different unit/note combinations do NOT merge
- Toggle active → checked → active
- Confirm purchase deletes only checked items

**4. Write integration tests for auth flow**

`tests/test_auth.py`:

- Register creates household + owner
- Login with correct credentials succeeds
- Login with wrong password fails
- Join household with valid invite code succeeds
- Join household with invalid code fails
- 6th member join fails

**5. Write integration tests for grocery flow**

`tests/test_grocery_routes.py`:

- Add item via POST returns success
- Toggle item via POST changes status
- Confirm purchase via POST removes checked items
- Unauthenticated requests redirect to login
- Cross-household access returns 403 or 404

**6. Write integration tests for favorites flow**

`tests/test_favorites.py`:

- Add favorite succeeds
- Duplicate favorite rejected
- Delete favorite removes it
- Quick-add creates grocery item

**7. Configure pytest**

`pytest.ini` or `pyproject.toml`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

#### Acceptance Criteria

- [ ] `pytest` runs all tests without errors
- [ ] All tests pass (green)
- [ ] Tests use an isolated test database (not the dev database)
- [ ] Each test function is independent (no test depends on another test's side effects)
- [ ] Coverage includes: validators, grocery UPSERT, auth flow, toggle, confirm, favorites
- [ ] At minimum 30+ test cases across all files

---
---

## PHASE 3: FRONTEND & UI

---

### Ticket 9: Tailwind CSS Setup & Base Templates

**Priority:** Critical  
**Dependencies:** Ticket 1  
**Estimated effort:** Small

#### Why This Matters

The app is mobile-first. Tailwind CSS provides utility classes for fast, responsive styling without writing custom CSS files. HTMX enables partial page updates without a JavaScript framework.

#### Reference

- UI specs: `Schema_API_UI_sub_specs.md` sections 3.1–3.5

#### Tasks

**1. Add Tailwind and HTMX via CDN to the base template**

For v1, using CDN links is simpler than a build step. Update `app/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{% block title %}Grocery List{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <style>
    /* Prevent iOS zoom on input focus */
    input, select, textarea { font-size: 16px; }
  </style>
</head>
<body class="bg-gray-50 min-h-screen pb-20">
  <!-- Flash messages -->
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
    <div id="flash-messages" class="fixed top-0 left-0 right-0 z-50 p-2">
      {% for category, message in messages %}
      <div class="max-w-lg mx-auto mb-2 p-3 rounded-lg text-sm
        {% if category == 'error' %}bg-red-100 text-red-700 border border-red-300
        {% elif category == 'success' %}bg-green-100 text-green-700 border border-green-300
        {% else %}bg-blue-100 text-blue-700 border border-blue-300{% endif %}">
        {{ message }}
      </div>
      {% endfor %}
    </div>
    {% endif %}
  {% endwith %}

  <!-- Main content -->
  <main class="max-w-lg mx-auto px-4 pt-4">
    {% block content %}{% endblock %}
  </main>

  <!-- Bottom navigation -->
  {% include '_bottom_nav.html' %}

  {% block scripts %}{% endblock %}
</body>
</html>
```

**2. Create the bottom navigation bar**

`app/templates/_bottom_nav.html`:

```html
{% if current_user.is_authenticated %}
<nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
  <div class="max-w-lg mx-auto flex justify-around py-2">
    <a href="{{ url_for('grocery.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/grocery') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <span>List</span>
    </a>
    <a href="{{ url_for('favorites.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/favorites') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
      </svg>
      <span>Favorites</span>
    </a>
    <a href="{{ url_for('household.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/household') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1"/>
      </svg>
      <span>Home</span>
    </a>
  </div>
</nav>
{% endif %}
```

**3. Create reusable macros**

`app/templates/_macros.html`:

```html
{% macro render_field(field) %}
<div class="mb-4">
  <label for="{{ field.id }}" class="block text-sm font-medium text-gray-700 mb-1">
    {{ field.label.text }}
  </label>
  {{ field(class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base", **kwargs) }}
  {% for error in field.errors %}
    <p class="mt-1 text-sm text-red-600">{{ error }}</p>
  {% endfor %}
</div>
{% endmacro %}

{% macro render_button(text, color="blue") %}
<button type="submit"
  class="w-full py-3 px-4 bg-{{ color }}-600 text-white rounded-lg font-medium text-base
         hover:bg-{{ color }}-700 active:bg-{{ color }}-800 transition-colors">
  {{ text }}
</button>
{% endmacro %}
```

**4. Style the auth templates**

Update `app/templates/auth/login.html`, `register.html`, and `join.html` using the macros and Tailwind classes. Each form should be centered, mobile-friendly, with large touch targets (minimum 44px height for buttons and inputs).

**5. Add HTMX CSRF configuration**

Add this script to `base.html` to automatically include the CSRF token with HTMX requests:

```html
<script>
  document.body.addEventListener('htmx:configRequest', function(event) {
    event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
  });
</script>
```

#### Acceptance Criteria

- [ ] Base template renders with Tailwind classes applied
- [ ] Bottom navigation shows 3 tabs (List, Favorites, Home) with active state highlighting
- [ ] Navigation is fixed to bottom and doesn't scroll with page content
- [ ] Flash messages display at the top with color coding (red for errors, green for success)
- [ ] All forms include CSRF tokens
- [ ] HTMX requests automatically include CSRF token in header
- [ ] Mobile viewport prevents unwanted zoom
- [ ] All input fields have minimum 16px font size (prevents iOS zoom)

---

### Ticket 10: Grocery List Page — Main UI

**Priority:** Critical  
**Dependencies:** Ticket 9, Ticket 5  
**Estimated effort:** Medium

#### Why This Matters

This is the page users open every day. It must be fast, clean, and finger-friendly on a phone. The layout has four sections: search/add at the top, favorite quick-add buttons, active items, and checked items with a confirm button.

#### Reference

- UI spec: `Schema_API_UI_sub_specs.md` sections 3.2–3.5
- HTMX behavior: `Route_Contract.md` section 7

#### Tasks

**1. Build the main grocery page template**

`app/templates/grocery/index.html`:

```html
{% extends "base.html" %}
{% block title %}Grocery List{% endblock %}

{% block content %}
<!-- Add item form with search -->
<section class="mb-4">
  <form hx-post="{{ url_for('grocery.add_item') }}"
        hx-target="#grocery-list"
        hx-swap="innerHTML"
        class="space-y-2">
    {{ form.hidden_tag() }}
    <div class="relative">
      {{ form.name(
        placeholder="Add item...",
        class="w-full p-4 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500",
        autocomplete="off",
        **{"hx-get": url_for('grocery.search'),
           "hx-trigger": "keyup changed delay:300ms",
           "hx-target": "#search-results",
           "hx-swap": "innerHTML",
           "name": "name"}
      ) }}
      <div id="search-results"
           class="absolute left-0 right-0 bg-white border border-gray-200 rounded-b-lg shadow-lg z-10 hidden">
      </div>
    </div>
    <div class="flex gap-2">
      {{ form.quantity(placeholder="Qty", class="w-20 p-3 border border-gray-300 rounded-lg text-base") }}
      {{ form.unit(placeholder="Unit", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
      {{ form.note(placeholder="Note", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
    </div>
    <button type="submit"
            class="w-full py-3 bg-blue-600 text-white rounded-lg font-medium text-lg
                   active:bg-blue-800 transition-colors">
      Add Item
    </button>
  </form>
</section>

<!-- Favorite quick-add buttons -->
{% if favorites %}
<section class="mb-4 flex gap-2 overflow-x-auto pb-2">
  {% for fav in favorites %}
  <button hx-post="{{ url_for('favorites.quick_add', favorite_id=fav.id) }}"
          hx-target="#grocery-list"
          hx-swap="innerHTML"
          class="flex-shrink-0 px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm
                 font-medium whitespace-nowrap active:bg-blue-200 transition-colors">
    {{ fav.name }}
  </button>
  {% endfor %}
</section>
{% endif %}

<!-- Grocery list (HTMX target) -->
<div id="grocery-list"
     hx-get="{{ url_for('grocery.fragment_list') }}"
     hx-trigger="every 15s"
     hx-swap="innerHTML">
  {% include 'grocery/_list.html' %}
</div>
{% endblock %}
```

**2. Build the list fragment template**

`app/templates/grocery/_list.html`:

```html
<!-- Active items -->
<section id="active-items" class="mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
    To Buy ({{ active_items|length }})
  </h2>
  {% if active_items %}
    {% for item in active_items %}
      {% include 'grocery/_item_row.html' %}
    {% endfor %}
  {% else %}
    <p class="text-gray-400 text-center py-8">No items yet. Add something above!</p>
  {% endif %}
</section>

<!-- Checked items -->
{% if checked_items %}
<section id="checked-items-container" class="mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
    Done ({{ checked_items|length }})
  </h2>
  {% include 'grocery/_checked_list.html' %}

  <!-- Confirm purchase button -->
  <button hx-post="{{ url_for('grocery.confirm') }}"
          hx-target="#checked-items-container"
          hx-swap="innerHTML"
          hx-confirm="Remove all checked items?"
          class="w-full mt-3 py-3 bg-green-600 text-white rounded-lg font-medium text-base
                 active:bg-green-800 transition-colors">
    Confirm Purchase ({{ checked_items|length }})
  </button>
</section>
{% endif %}
```

**3. Build the item row fragment**

`app/templates/grocery/_item_row.html`:

```html
<div hx-post="{{ url_for('grocery.toggle', item_id=item.id) }}"
     hx-target="this"
     hx-swap="outerHTML"
     class="flex items-center justify-between p-4 border-b border-gray-100 cursor-pointer
            {% if item.status == 'checked' %}bg-gray-50{% else %}bg-white active:bg-gray-50{% endif %}
            transition-colors">
  <div class="flex items-center gap-3 flex-1 min-w-0">
    <div class="w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0
                {% if item.status == 'checked' %}border-green-500 bg-green-500{% else %}border-gray-300{% endif %}">
      {% if item.status == 'checked' %}
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
        </svg>
      {% endif %}
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-base truncate
                {% if item.status == 'checked' %}line-through text-gray-400{% else %}text-gray-900{% endif %}">
        {{ item.name }}
      </p>
      {% if item.note %}
      <p class="text-xs text-gray-400 truncate">{{ item.note }}</p>
      {% endif %}
    </div>
  </div>
  <div class="text-right flex-shrink-0 ml-2
              {% if item.status == 'checked' %}text-gray-400{% else %}text-gray-600{% endif %}">
    <span class="text-sm font-medium">{{ item.quantity_value }}{% if item.unit %} {{ item.unit }}{% endif %}</span>
  </div>
</div>
```

**4. Build the checked list and search results fragments**

`app/templates/grocery/_checked_list.html`:

```html
{% for item in checked_items %}
  {% include 'grocery/_item_row.html' %}
{% endfor %}
```

`app/templates/grocery/_search_results.html`:

```html
{% if results and (results.favorites or results.history) %}
<ul class="py-1">
  {% for fav in results.favorites %}
  <li class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 text-base"
      onclick="document.querySelector('[name=name]').value='{{ fav.name }}'; document.getElementById('search-results').classList.add('hidden')">
    <span class="text-yellow-500 mr-1">★</span> {{ fav.name }}
    {% if fav.default_unit %}({{ fav.default_unit }}){% endif %}
  </li>
  {% endfor %}
  {% for name in results.history %}
  <li class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 text-base"
      onclick="document.querySelector('[name=name]').value='{{ name }}'; document.getElementById('search-results').classList.add('hidden')">
    {{ name }}
  </li>
  {% endfor %}
</ul>
{% endif %}
```

**5. Add JavaScript for search dropdown visibility**

Add to `base.html` or a separate JS file:

```html
<script>
  document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'search-results') {
      const el = event.detail.target;
      el.classList.toggle('hidden', el.innerHTML.trim() === '');
    }
  });
  document.addEventListener('click', function(event) {
    const sr = document.getElementById('search-results');
    if (sr && !sr.contains(event.target)) {
      sr.classList.add('hidden');
    }
  });
</script>
```

#### Acceptance Criteria

- [ ] Grocery page loads with all sections visible on mobile
- [ ] Typing in the search field triggers live suggestions after 300ms
- [ ] Selecting a suggestion fills the item name field
- [ ] Submitting the form adds the item and refreshes the list (no full page reload with HTMX)
- [ ] Tapping an item row toggles its checked/active state
- [ ] Active items show with clear styling; checked items show with strikethrough and grey
- [ ] "Confirm Purchase" button only appears when checked items exist
- [ ] Confirm shows a confirmation dialog before executing
- [ ] Favorite quick-add buttons are scrollable horizontally
- [ ] All touch targets are at least 44px tall
- [ ] The page auto-refreshes the list every 15 seconds via HTMX polling

---

### Ticket 11: Favorites Page & Auth Templates Styling

**Priority:** High  
**Dependencies:** Ticket 10  
**Estimated effort:** Medium

#### Why This Matters

The favorites management page and the auth pages (login, register, join) need full styling to be usable on mobile.

#### Tasks

**1. Build the favorites management page**

`app/templates/favorites/index.html`:

```html
{% extends "base.html" %}
{% block title %}Favorites{% endblock %}

{% block content %}
<h1 class="text-xl font-bold text-gray-900 mb-4">Manage Favorites</h1>

<!-- Add favorite form -->
<form hx-post="{{ url_for('favorites.create') }}"
      hx-target="#favorites-list"
      hx-swap="innerHTML"
      class="mb-6 space-y-2 p-4 bg-white rounded-lg shadow-sm">
  {{ form.hidden_tag() }}
  {{ form.name(placeholder="Item name", class="w-full p-3 border border-gray-300 rounded-lg text-base") }}
  <div class="flex gap-2">
    {{ form.quantity(placeholder="Qty", class="w-20 p-3 border border-gray-300 rounded-lg text-base") }}
    {{ form.unit(placeholder="Unit", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
    {{ form.note(placeholder="Note", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
  </div>
  <button type="submit"
          class="w-full py-3 bg-yellow-500 text-white rounded-lg font-medium text-base
                 active:bg-yellow-700 transition-colors">
    Add to Favorites
  </button>
</form>

<!-- Favorites list -->
<div id="favorites-list">
  {% include 'favorites/_list.html' %}
</div>
{% endblock %}
```

**2. Build the favorites list fragment**

`app/templates/favorites/_list.html`:

```html
{% if favorites %}
<ul class="space-y-2">
  {% for fav in favorites %}
  <li class="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
    <div class="flex-1 min-w-0">
      <p class="text-base font-medium text-gray-900 truncate">{{ fav.name }}</p>
      <p class="text-xs text-gray-400">
        {{ fav.default_quantity_value }}{% if fav.default_unit %} {{ fav.default_unit }}{% endif %}
        {% if fav.default_note %} · {{ fav.default_note }}{% endif %}
      </p>
    </div>
    <div class="flex gap-2 ml-2">
      <button hx-post="{{ url_for('favorites.quick_add', favorite_id=fav.id) }}"
              class="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium
                     active:bg-blue-200 transition-colors">
        + List
      </button>
      <button hx-post="{{ url_for('favorites.delete', favorite_id=fav.id) }}"
              hx-target="closest li"
              hx-swap="outerHTML"
              hx-confirm="Remove this favorite?"
              class="px-3 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium
                     active:bg-red-200 transition-colors">
        Delete
      </button>
    </div>
  </li>
  {% endfor %}
</ul>
{% else %}
<p class="text-gray-400 text-center py-8">No favorites yet. Add one above!</p>
{% endif %}
```

**3. Style the auth pages**

Update `login.html`, `register.html`, and `join.html` with full Tailwind styling:

- Centered card layout
- Large, clear form fields
- Submit buttons at least 44px tall
- Links between login/register/join pages
- Error messages displayed inline below fields

**4. Build the household page**

`app/templates/household/index.html`:

```html
{% extends "base.html" %}
{% block title %}Household{% endblock %}

{% block content %}
<h1 class="text-xl font-bold text-gray-900 mb-4">{{ household.name }}</h1>

{% if is_owner %}
<div class="p-4 bg-white rounded-lg shadow-sm mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase mb-2">Invite Code</h2>
  <p class="text-2xl font-mono font-bold text-blue-600 tracking-widest text-center py-2">
    {{ household.invite_code }}
  </p>
  <p class="text-xs text-gray-400 text-center mb-3">Share this code for others to join</p>
  <form method="POST" action="{{ url_for('household.rotate_code') }}">
    {{ csrf_token() | safe }}
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit"
            class="w-full py-2 bg-gray-200 text-gray-700 rounded-lg text-sm
                   active:bg-gray-300 transition-colors">
      Generate New Code
    </button>
  </form>
</div>
{% endif %}

<div class="p-4 bg-white rounded-lg shadow-sm">
  <h2 class="text-sm font-semibold text-gray-500 uppercase mb-2">
    Members ({{ members|length }}/5)
  </h2>
  <ul class="divide-y divide-gray-100">
    {% for member in members %}
    <li class="flex items-center justify-between py-3">
      <span class="text-base text-gray-900">{{ member.username }}</span>
      <span class="text-xs px-2 py-1 rounded-full
        {% if member.role == 'owner' %}bg-yellow-100 text-yellow-700{% else %}bg-gray-100 text-gray-500{% endif %}">
        {{ member.role }}
      </span>
    </li>
    {% endfor %}
  </ul>
</div>

<form method="POST" action="{{ url_for('auth.logout') }}" class="mt-6">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <button type="submit"
          class="w-full py-3 bg-red-100 text-red-700 rounded-lg font-medium text-base
                 active:bg-red-200 transition-colors">
    Log Out
  </button>
</form>
{% endblock %}
```

**5. Quick-add feedback fragment**

`app/templates/favorites/_quick_add_feedback.html`:

```html
{% if success %}
<span class="text-green-600 text-sm animate-pulse">Added!</span>
{% endif %}
```

#### Acceptance Criteria

- [ ] Favorites page displays all household favorites in order
- [ ] "Add to Favorites" form works without page reload (HTMX)
- [ ] "Delete" removes the favorite row without page reload
- [ ] "+ List" quick-adds the item to the grocery list
- [ ] Login, register, and join pages are styled and usable on mobile
- [ ] Household page shows invite code to owner, member list to everyone
- [ ] Logout button works
- [ ] All pages have consistent styling via `base.html`

---
---

## PHASE 4: DEVOPS & DEPLOYMENT

---

### Ticket 12: Docker & Docker Compose Setup

**Priority:** Critical  
**Dependencies:** Ticket 1, Ticket 2  
**Estimated effort:** Small–Medium

#### Why This Matters

Docker packages the app and database into containers that run the same way everywhere — your laptop, a VPS, or a Raspberry Pi. Docker Compose orchestrates both containers together.

#### Reference

- `compose.prod.yaml` (already in repo)
- `Hostinger_Deployment_Reference.md` sections 1–5

#### Tasks

**1. Create the Dockerfile**

`Dockerfile` (at project root):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
```

**What each line does:**
- `FROM python:3.12-slim` — start with a minimal Python image.
- `WORKDIR /app` — set the working directory inside the container.
- `COPY requirements.txt .` then `RUN pip install` — install Python dependencies first (Docker caches this layer).
- `COPY . .` — copy the rest of the code.
- `CMD` — the command that runs when the container starts. Gunicorn is a production-grade Python web server.

**2. Create `.dockerignore`**

```text
__pycache__
*.pyc
.env
.env.prod
.git
.gitignore
*.md
tests/
.venv/
node_modules/
```

**3. Create `docker-compose.yml` for local development**

```yaml
services:
  web:
    build: .
    container_name: grocery_web_dev
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - SECRET_KEY=dev-secret-change-me
      - DATABASE_URL=postgresql+psycopg://grocery:grocery@db:5432/grocery_dev
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
    command: flask run --host=0.0.0.0 --debug

  db:
    image: postgres:16-alpine
    container_name: grocery_db_dev
    environment:
      - POSTGRES_USER=grocery
      - POSTGRES_PASSWORD=grocery
      - POSTGRES_DB=grocery_dev
    ports:
      - "5432:5432"
    volumes:
      - dev_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grocery -d grocery_dev"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  dev_pg_data:
```

**4. Verify the production compose file**

The file `compose.prod.yaml` already exists in the repo. Verify it matches the spec from `Production_Cutover_Runbook.md` section 7. Key points:

- Web binds to `127.0.0.1:18080` only (not `0.0.0.0`)
- Uses `env_file` pointing to `/opt/grocery-app/shared/env/.env.prod`
- Both services on `grocery_net` network
- Health checks present on both services

**5. Add a health check endpoint**

In `app/__init__.py`, add inside `create_app()`:

```python
@app.route("/health")
def health():
    return "OK", 200
```

**6. Test the full stack locally**

```bash
docker compose up --build
# In another terminal:
docker compose exec web flask db upgrade
# Open http://localhost:5000/login
```

#### Acceptance Criteria

- [ ] `docker compose up --build` starts both web and db containers
- [ ] Web container connects to the database
- [ ] `flask db upgrade` runs successfully inside the web container
- [ ] App is accessible at `http://localhost:5000`
- [ ] `/health` returns `200 OK`
- [ ] Database data persists after `docker compose down && docker compose up`
- [ ] Production compose file binds to `127.0.0.1:18080` only

---

### Ticket 13: Production Deployment Configuration

**Priority:** High  
**Dependencies:** Ticket 12  
**Estimated effort:** Medium

> **Canonical source:** `tickets/13_production_deployment.md`. The summary below is kept in this aggregate file for orientation, but the per-ticket file is authoritative.

#### Why This Matters

This ticket prepares everything needed for production deployment on the Hostinger VPS. Remote access is provided by a **host-based Nginx reverse proxy** bound to `grocery.<your-domain>`, with HTTPS supplied by a **Let's Encrypt certificate** issued by Certbot. The web container stays bound to `127.0.0.1:18080` and is never exposed to the public interface.

#### Reference

- `tickets/13_production_deployment.md` (canonical per-ticket spec)
- `Production_Cutover_Runbook.md` (full go-live guide)
- `Hostinger_Deployment_Reference.md` (operational quick reference)
- `docker/nginx/grocery.conf.example` (Nginx site template)
- `.env.prod.example` (already in repo)

#### Tasks

**1. Verify `.env.prod.example` is complete**

The file should contain all environment variables the app needs. Compare against `app/config.py` and the Production Cutover Runbook section 6.

**2. Configure Gunicorn for production**

The `Dockerfile` CMD already uses Gunicorn. Verify settings:

- `--workers 2` (sufficient for 2–5 users)
- `--bind 0.0.0.0:5000` (container-internal, host binding is handled by compose)
- `--timeout 120` (generous timeout for slow operations)

**3. Ensure migration command works in container**

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
```

**4. Add production security settings to `app/config.py`**

`ProductionConfig` must read all cookie/security settings from environment, and `app/__init__.py` must wrap the WSGI app in `werkzeug.middleware.proxy_fix.ProxyFix(..., x_for=1, x_proto=1, x_host=1)` so Flask trusts the `X-Forwarded-*` headers Nginx sets. Without `ProxyFix`, `SESSION_COOKIE_SECURE=true` will refuse to set session cookies because Flask thinks the request is HTTP.

**5. Configure host-based Nginx reverse proxy with Let's Encrypt TLS**

- Add a DNS A record for `grocery.<your-domain>` pointing at the VPS public IP; verify with `dig grocery.<your-domain> +short`.
- Install Nginx + Certbot on the VPS: `sudo apt install -y nginx certbot python3-certbot-nginx`.
- Open firewall ports 80 and 443.
- Place a minimal HTTP-only server block in `/etc/nginx/sites-available/grocery` with `server_name grocery.<your-domain>;` and `proxy_pass http://127.0.0.1:18080;`.
- Run `sudo certbot --nginx -d grocery.<your-domain>` — this issues a trusted cert, rewrites Nginx to add the HTTPS block and HTTP→HTTPS redirect, and installs a systemd timer for auto-renewal.
- Verify renewal with `sudo certbot renew --dry-run`.

**6. Document the deployment steps**

Ensure the Production Cutover Runbook is accurate and can be followed step by step.

#### Acceptance Criteria

- [ ] `.env.prod.example` contains all required env vars
- [ ] Building the Docker image succeeds: `docker build -t grocery-app:v1.0.0 .`
- [ ] Production compose starts and health checks pass
- [ ] Migration runs successfully in the production container
- [ ] Secure cookies are enabled when `SESSION_COOKIE_SECURE=true`
- [ ] DNS A record for `grocery.<your-domain>` resolves to the VPS public IP
- [ ] Nginx reverse proxy forwards HTTPS traffic for `grocery.<your-domain>` to `127.0.0.1:18080`
- [ ] Let's Encrypt cert is loaded from `/etc/letsencrypt/live/grocery.<your-domain>/`
- [ ] `curl -fsS https://grocery.<your-domain>/health` returns `200 OK` (no `-k` flag needed)
- [ ] `sudo certbot renew --dry-run` reports "all renewals succeeded"
- [ ] App reachable at `https://grocery.<your-domain>/login` from an external device with no browser warning
- [ ] Web container is NOT exposed on the public interface (only `127.0.0.1:18080`)
- [ ] Production Cutover Runbook matches actual file structure and commands

---

### Ticket 14: Backup Strategy & Health Monitoring

**Priority:** Medium  
**Dependencies:** Ticket 12  
**Estimated effort:** Small

#### Why This Matters

The database contains all household data and user credentials. If it's lost, everything is lost. Daily backups are mandatory.

#### Reference

- `Production_Cutover_Runbook.md` sections 9.2, 12

#### Tasks

**1. Create the backup script**

`scripts/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/grocery-app/shared/backups"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="/opt/grocery-app/releases/current/compose.prod.yaml"
ENV_FILE="/opt/grocery-app/shared/env/.env.prod"

echo "[$(date)] Starting backup..."

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  pg_dump -U grocery -d grocery \
  > "${BACKUP_DIR}/grocery_${DATE}.sql"

gzip "${BACKUP_DIR}/grocery_${DATE}.sql"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "[$(date)] Backup complete: grocery_${DATE}.sql.gz"
```

Make it executable: `chmod +x scripts/backup.sh`

**2. Document cron setup**

Add a cron job on the server (not inside Docker):

```bash
crontab -e
# Add this line for daily 3 AM backup:
0 3 * * * /opt/grocery-app/releases/current/scripts/backup.sh >> /opt/grocery-app/shared/logs/backup.log 2>&1
```

**3. Document the restore procedure**

Add to the backup script or a separate `scripts/restore.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_FILE="$1"
COMPOSE_FILE="/opt/grocery-app/releases/current/compose.prod.yaml"
ENV_FILE="/opt/grocery-app/shared/env/.env.prod"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <backup-file.sql.gz>"
  exit 1
fi

echo "Restoring from: $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" > /tmp/restore.sql

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  psql -U grocery -d grocery < /tmp/restore.sql

rm -f /tmp/restore.sql
echo "Restore complete."
```

**4. Enhance the health check endpoint**

Update the `/health` route to also verify database connectivity:

```python
@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return "OK", 200
    except Exception:
        return "Database unreachable", 503
```

#### Acceptance Criteria

- [ ] Backup script runs without errors when invoked manually
- [ ] Backup file is compressed (`.gz`)
- [ ] Backups older than 7 days are automatically deleted
- [ ] Restore script can restore from a backup file
- [ ] `/health` returns `200` when DB is up and `503` when DB is down
- [ ] Cron job documentation is complete

---
---

## PHASE 5: HARDENING & POLISH

---

### Ticket 15: Security Hardening & Rate Limiting

**Priority:** High  
**Dependencies:** All prior tickets  
**Estimated effort:** Medium

#### Why This Matters

Even a private app handles passwords and personal data. This ticket adds rate limiting, security headers, and a final validation review.

#### Tasks

**1. Add rate limiting**

Install `Flask-Limiter`:

Add to `requirements.txt`:
```text
Flask-Limiter>=3.5,<4
```

Add to `app/extensions.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
```

Initialize in `create_app()`:
```python
limiter.init_app(app)
```

Apply limits in `app/auth/routes.py`:
```python
from app.extensions import limiter

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    ...

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    ...
```

**2. Add security headers**

Add an `after_request` handler in `create_app()`:

```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

**3. Review all templates for XSS safety**

Jinja2 auto-escapes by default. Verify:
- No use of `{{ ... | safe }}` with user-supplied data
- No `{% autoescape false %}` blocks
- All user input displayed via template variables (not raw HTML)

**4. Review all validation**

Walk through every route that accepts user input and verify:
- Server-side validation is performed (not just client-side)
- Item names are validated with `validate_item_name()`
- Quantities are validated with `validate_quantity()`
- Notes and units are length-checked
- Invite codes are validated

**5. Review CSRF protection**

Verify:
- All POST forms include `{{ form.hidden_tag() }}` or a CSRF token input
- HTMX requests include the CSRF token via the `htmx:configRequest` handler
- `CSRFProtect` is initialized in `extensions.py` and attached to the app

#### Acceptance Criteria

- [ ] Login endpoint returns `429 Too Many Requests` after 5 failed attempts in one minute
- [ ] Registration endpoint returns `429` after 3 attempts per hour
- [ ] Security headers present on all responses (`X-Content-Type-Options`, `X-Frame-Options`)
- [ ] No `| safe` filter used on user-supplied data in any template
- [ ] All POST routes validate CSRF tokens
- [ ] All user inputs are validated server-side

---

### Ticket 16: Documentation & Final Polish

**Priority:** Medium  
**Dependencies:** All prior tickets  
**Estimated effort:** Small

#### Why This Matters

Documentation lets someone else (or future you) set up and maintain the project. Final polish ensures the app feels solid in daily use.

#### Tasks

**1. Write `README.md`**

Include:
- Project overview (1 paragraph)
- Tech stack summary
- Prerequisites (Python 3.12+, Docker, PostgreSQL)
- Local development setup (step by step)
- Running tests
- Docker Compose usage
- Production deployment (link to `Production_Cutover_Runbook.md`)
- Environment variables table

**2. Add loading states**

For HTMX interactions, add visual feedback:
- `hx-indicator` class on buttons to show a spinner while requests are in flight
- Add CSS for `.htmx-request` state

Example:
```html
<button type="submit" class="... htmx-indicator-parent">
  <span class="htmx-indicator hidden">
    <svg class="animate-spin h-5 w-5" ...></svg>
  </span>
  Add Item
</button>
```

**3. Add empty states**

Every list page should have a friendly message when empty:
- Empty grocery list: "No items yet. Add something above!"
- Empty favorites: "No favorites yet. Add your first one!"
- Empty checked items: (section hidden entirely)

**4. Accessibility review**

- All `<input>` fields have `<label>` elements
- All buttons have descriptive text (not just icons)
- Color contrast ratio meets WCAG AA (4.5:1 for text)
- Focus indicators are visible on all interactive elements
- `aria-label` on icon-only buttons

**5. Final functional walkthrough**

Test the complete happy path on a phone:
1. Register → creates household
2. Copy invite code → second user joins
3. Add items → they appear on the list
4. Toggle items → they move to checked
5. Confirm purchase → checked items removed
6. Add favorites → quick-add works
7. Logout / Login cycle works

#### Acceptance Criteria

- [ ] `README.md` lets a new developer set up the project in under 30 minutes
- [ ] All pages have appropriate empty states
- [ ] Loading indicators appear during HTMX requests
- [ ] All form inputs have labels
- [ ] App is functional end-to-end on a mobile browser
- [ ] No JavaScript console errors in any flow

---
---

## Ticket Dependency Graph

```
Ticket 1  (Project Structure)
   ├── Ticket 2  (Database)
   │      └── Ticket 3  (Common Utilities)
   │             ├── Ticket 4  (Auth)
   │             │      ├── Ticket 5  (Grocery)
   │             │      │      ├── Ticket 6  (Favorites)
   │             │      │      └── Ticket 8  (Tests)
   │             │      └── Ticket 7  (Household)
   │             │             └── Ticket 8  (Tests)
   │             └──────────────── Ticket 8  (Tests)
   ├── Ticket 9  (Tailwind & Templates)
   │      └── Ticket 10 (Grocery UI)
   │             └── Ticket 11 (Favorites UI & Auth Styling)
   └── Ticket 12 (Docker)
          ├── Ticket 13 (Production Deploy)
          └── Ticket 14 (Backups & Monitoring)

Ticket 15 (Security Hardening)  ← depends on all above
Ticket 16 (Documentation & Polish) ← depends on all above
```

---

## Definition of Done (v1)

The v1 release is complete when **all** of the following are true:

- [ ] A household can be created and joined by up to 5 users
- [ ] Grocery items can be added, viewed, checked, unchecked, and confirmed for removal
- [ ] Duplicate items merge quantities atomically (no race conditions)
- [ ] Favorites can be managed and used for one-tap quick-add
- [ ] The mobile UI is comfortable for daily grocery shopping use
- [ ] All core tests pass (`pytest` green)
- [ ] Database migrations are reproducible from an empty database
- [ ] Docker Compose starts both services with health checks passing
- [ ] Production deployment follows the Cutover Runbook successfully
- [ ] Security hardening checklist completed
- [ ] `README.md` and deployment docs are written
