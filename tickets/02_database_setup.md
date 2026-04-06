# Ticket 2: Database Setup — PostgreSQL, SQLAlchemy & Alembic

**Phase:** 1 — Foundation  
**Priority:** Critical  
**Dependencies:** Ticket 1  
**Estimated effort:** Medium

---

## Why This Matters

This ticket creates all the database tables the app needs. We use SQLAlchemy (an ORM that lets us write Python classes instead of raw SQL) and Alembic (a migration tool that tracks schema changes over time so they can be applied in order).

## Reference

- Full schema: `Schema_API_UI_sub_specs.md` sections 1.1–1.4
- Dedupe index: `Concurrency_Duplicate_Merge_Design.md` section 3

---

## Tasks

### 1. Make sure a local PostgreSQL database is running

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

### 2. Initialize Flask-Migrate (Alembic wrapper)

From the project root, with your virtual environment active:

```bash
flask db init
```

This creates a `migrations/` folder with Alembic config files. Open `migrations/env.py` and make sure it imports your models so Alembic can auto-detect them. Add near the top:

```python
from app.extensions import db
target_metadata = db.metadata
```

### 3. Create SQLAlchemy models

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

### 4. Import models in the app factory

In `app/__init__.py`, add this import inside `create_app()` **before** `migrate.init_app(...)`:

```python
import app.models  # noqa: F401 — ensures Alembic sees all models
```

### 5. Create the active dedupe partial unique index migration

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

### 6. Configure the Flask-Login user loader

In `app/extensions.py` or `app/auth/__init__.py`, add:

```python
@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return db.session.get(User, int(user_id))
```

### 7. Apply migrations

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

---

## Acceptance Criteria

- [ ] `flask db upgrade` creates all 5 tables from an empty database
- [ ] `flask db downgrade base` removes all tables cleanly
- [ ] Running `flask db upgrade` a second time is a no-op (idempotent)
- [ ] The partial unique index `uq_grocery_active_dedupe` exists on `grocery_item`
- [ ] All foreign keys reference the correct parent tables
- [ ] Model relationships work: you can create a Household, add a User to it, and query `household.users`
