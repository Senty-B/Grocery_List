# Ticket 6: Favorites Module — Quick-Add & Management

**Phase:** 2 — Core Backend  
**Priority:** High  
**Dependencies:** Ticket 5  
**Estimated effort:** Medium

---

## Why This Matters

Favorites let users save commonly bought items for one-tap adding. The first 8 favorites appear on the grocery page as quick-add buttons, reducing friction for daily use.

## Reference

- Routes: `Route_Contract.md` section 6
- Schema: `Schema_API_UI_sub_specs.md` section 1.4

---

## Tasks

### 1. Create the favorites service layer

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

### 2. Create the favorites form

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

### 3. Create the favorites routes

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

### 4. Create placeholder templates

- `app/templates/favorites/index.html`
- `app/templates/favorites/_list.html`
- `app/templates/favorites/_quick_add_feedback.html`

---

## Acceptance Criteria

- [ ] A user can add an item to favorites
- [ ] Duplicate favorite names (same household) are rejected
- [ ] Favorites are returned ordered by `sort_order`
- [ ] Deleting a favorite removes it from the database
- [ ] Quick-add creates a grocery item using the favorite's defaults
- [ ] Quick-add uses the same UPSERT logic (merges if duplicate active item exists)
- [ ] Reorder changes the `sort_order` value
- [ ] All routes are protected by `@login_required` and `@require_household`
- [ ] A user cannot access another household's favorites
