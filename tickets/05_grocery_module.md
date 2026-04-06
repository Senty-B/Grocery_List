# Ticket 5: Grocery Module — Add, Toggle, Confirm & Search

**Phase:** 2 — Core Backend  
**Priority:** Critical  
**Dependencies:** Ticket 4  
**Estimated effort:** Medium–Large

---

## Why This Matters

This is the core feature of the entire application. Users add grocery items, check them off while shopping, and confirm purchases to clean the list. The duplicate-merge logic (UPSERT) is the most technically important part — it prevents race conditions when two users add the same item at the same time.

## Reference

- Routes: `Route_Contract.md` section 5
- Duplicate merge: `Concurrency_Duplicate_Merge_Design.md` (full document)
- Schema: `Schema_API_UI_sub_specs.md` section 1.3

---

## Tasks

### 1. Create the grocery service layer

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

### 2. Create the grocery form

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

### 3. Create the grocery routes

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

### 4. Create placeholder templates

Create these minimal templates (full styling in Ticket 10):

- `app/templates/grocery/index.html` — main page
- `app/templates/grocery/_list.html` — HTMX fragment for the full list
- `app/templates/grocery/_item_row.html` — single item row fragment
- `app/templates/grocery/_checked_list.html` — checked items section
- `app/templates/grocery/_search_results.html` — search dropdown

---

## Acceptance Criteria

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
