import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.common.authz import require_household
from app.common.exceptions import NotFoundError
from app.grocery.forms import AddItemForm
from app.grocery.services import (
    add_grocery_item,
    confirm_purchase,
    get_grocery_list,
    search_items,
    toggle_item_status,
)
from app.models.favorite_item import FavoriteItem

logger = logging.getLogger(__name__)
grocery_bp = Blueprint("grocery", __name__)


def _is_htmx():
    return request.headers.get("HX-Request") == "true"


def _render_grocery_list():
    active_items, checked_items = get_grocery_list(current_user.household_id)
    return render_template(
        "grocery/_list.html",
        active_items=active_items,
        checked_items=checked_items,
    )


@grocery_bp.route("/")
@login_required
@require_household
def index():
    active_items, checked_items = get_grocery_list(current_user.household_id)
    favorites = (
        FavoriteItem.query.filter_by(household_id=current_user.household_id)
        .order_by(FavoriteItem.sort_order, FavoriteItem.name)
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
                return _render_grocery_list()
            flash("Item added.", "success")
        except ValueError as error:
            flash(str(error), "error")
    elif not _is_htmx():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")

    if _is_htmx():
        return _render_grocery_list()
    return redirect(url_for("grocery.index"))


@grocery_bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@login_required
@require_household
def toggle(item_id):
    try:
        toggle_item_status(item_id, current_user.household_id, current_user.id)
        if _is_htmx():
            return _render_grocery_list()
    except ValueError as error:
        if str(error) == "Item not found.":
            raise NotFoundError(str(error))
        flash(str(error), "error")

    return redirect(url_for("grocery.index"))


@grocery_bp.route("/confirm", methods=["POST"])
@login_required
@require_household
def confirm():
    try:
        count = confirm_purchase(current_user.household_id)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("grocery.index"))

    if _is_htmx():
        return render_template("grocery/_checked_list.html", checked_items=[])

    flash(f"{count} item(s) removed.", "success")
    return redirect(url_for("grocery.index"))


@grocery_bp.route("/search")
@login_required
@require_household
def search():
    query = request.args.get("q") or request.args.get("name") or ""
    results = search_items(current_user.household_id, query)
    return render_template(
        "grocery/_search_results.html",
        query=query,
        results=results,
    )


@grocery_bp.route("/fragments/list")
@login_required
@require_household
def fragment_list():
    return _render_grocery_list()
