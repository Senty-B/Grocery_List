# Concurrency-Safe Duplicate Merge Design (V1)

> **Status:** Canonical implementation pattern for add-item duplicate merging  
> **Goal:** Prevent race-created duplicate active grocery rows under concurrent adds

---

## 1) Problem

V1 requires this behavior:

- if an active duplicate exists, increment quantity
- otherwise insert a new active row

The app-level "select then insert/update" approach is race-prone when two users add the same item at almost the same time.

---

## 2) Chosen Solution (Simple + Reliable)

Use PostgreSQL as concurrency arbiter:

1. Add canonical normalized fields for dedupe key:
   - `normalized_name` (already present)
   - `normalized_unit` (`TEXT NOT NULL DEFAULT ''`)
   - `normalized_note` (`TEXT NOT NULL DEFAULT ''`)
2. Add partial unique index for active rows only:
   - unique on `(household_id, normalized_name, normalized_unit, normalized_note)`
   - predicate `WHERE status = 'active'`
3. Use one atomic UPSERT statement for add-item:
   - `INSERT ... ON CONFLICT ... DO UPDATE quantity = quantity + EXCLUDED.quantity`

This removes race windows and keeps business behavior aligned with product rules.

---

## 3) Schema Rule

```sql
CREATE UNIQUE INDEX uq_grocery_active_dedupe
ON grocery_item (household_id, normalized_name, normalized_unit, normalized_note)
WHERE status = 'active';
```

Important:

- `normalized_unit` and `normalized_note` must be non-null (`''` as empty canonical value).
- The predicate keeps checked rows outside this active dedupe uniqueness rule.

---

## 4) Migration Template (Alembic)

```python
"""add active dedupe uniqueness for grocery_item

Revision ID: 20260405_add_active_dedupe
Revises: <prev_revision_id>
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_add_active_dedupe"
down_revision = "<prev_revision_id>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "grocery_item",
        sa.Column("normalized_unit", sa.String(length=20), nullable=False, server_default=""),
    )
    op.add_column(
        "grocery_item",
        sa.Column("normalized_note", sa.String(length=255), nullable=False, server_default=""),
    )

    # Backfill from existing columns in canonical form.
    op.execute(
        """
        UPDATE grocery_item
        SET
          normalized_unit = lower(regexp_replace(trim(coalesce(unit, '')), '\\s+', ' ', 'g')),
          normalized_note = lower(regexp_replace(trim(coalesce(note, '')), '\\s+', ' ', 'g'))
        """
    )

    # Remove server defaults after backfill so app sets values explicitly.
    op.alter_column("grocery_item", "normalized_unit", server_default=None)
    op.alter_column("grocery_item", "normalized_note", server_default=None)

    op.create_index(
        "uq_grocery_active_dedupe",
        "grocery_item",
        ["household_id", "normalized_name", "normalized_unit", "normalized_note"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_grocery_active_dedupe", table_name="grocery_item")
    op.drop_column("grocery_item", "normalized_note")
    op.drop_column("grocery_item", "normalized_unit")
```

---

## 5) Service-Layer Pattern (SQLAlchemy + PostgreSQL UPSERT)

```python
from sqlalchemy import text


UPSERT_GROCERY_ITEM_SQL = text(
    """
    INSERT INTO grocery_item (
      household_id,
      name,
      normalized_name,
      unit,
      normalized_unit,
      note,
      normalized_note,
      quantity_value,
      status,
      created_by_user_id,
      created_at,
      updated_at
    )
    VALUES (
      :household_id,
      :name,
      :normalized_name,
      :unit,
      :normalized_unit,
      :note,
      :normalized_note,
      :quantity_value,
      'active',
      :created_by_user_id,
      NOW(),
      NOW()
    )
    ON CONFLICT (household_id, normalized_name, normalized_unit, normalized_note)
    WHERE status = 'active'
    DO UPDATE SET
      quantity_value = grocery_item.quantity_value + EXCLUDED.quantity_value,
      updated_at = NOW()
    RETURNING id, quantity_value, status
    """
)


def add_grocery_item_atomic(session, payload):
    row = session.execute(UPSERT_GROCERY_ITEM_SQL, payload).mappings().one()
    return dict(row)
```

---

## 6) Normalization Contract

Apply same normalization in validation/service layer and migration backfill:

- trim leading/trailing whitespace
- collapse repeated spaces
- lowercase
- null => empty string for normalized unit/note

Display fields (`name`, `unit`, `note`) keep original user-facing values.

---

## 7) Required Tests

1. Single user adds duplicate active item twice -> one row, quantity summed.
2. Two concurrent requests adding same dedupe key -> one row, quantity summed.
3. Checked item exists, then add same key -> new active row allowed.
4. Different note/unit combinations do not merge.
5. Null/empty unit/note normalize to same dedupe key.

---

## 8) Operational Notes

- This pattern is PostgreSQL-specific by design and is acceptable for v1.
- Do not replace this with in-process locks or Python queues.
- If dedupe rules change in v2, update index + upsert together as one migration.

