import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.common.authz import require_household
from app.common.exceptions import NotFoundError
from app.favorites.forms import AddFavoriteForm
from app.favorites.services import (
    add_favorite,
    get_favorites_list,
    quick_add_from_favorite,
    remove_favorite,
    reorder_favorite,
)
from app.grocery.services import get_grocery_list

logger = logging.getLogger(__name__)
favorites_bp = Blueprint("favorites", __name__)


def _is_htmx():
    return request.headers.get("HX-Request") == "true"


def _render_favorites_list():
    favorites = get_favorites_list(current_user.household_id)
    return render_template("favorites/_list.html", favorites=favorites)


@favorites_bp.route("/")
@login_required
@require_household
def index():
    favorites = get_favorites_list(current_user.household_id)
    form = AddFavoriteForm()
    return render_template("favorites/index.html", favorites=favorites, form=form)


@favorites_bp.route("", methods=["POST"])
@login_required
@require_household
def create():
    form = AddFavoriteForm()
    if form.validate_on_submit():
        try:
            add_favorite(
                household_id=current_user.household_id,
                user_id=current_user.id,
                name=form.name.data,
                quantity=form.quantity.data or 1,
                unit=form.unit.data,
                note=form.note.data,
            )
            if _is_htmx():
                return _render_favorites_list()
            flash("Favorite added.", "success")
        except ValueError as error:
            flash(str(error), "error")
    elif not _is_htmx():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")

    if _is_htmx():
        return _render_favorites_list()
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/delete", methods=["POST"])
@login_required
@require_household
def delete(favorite_id):
    try:
        remove_favorite(favorite_id, current_user.household_id, current_user.id)
        if _is_htmx():
            return _render_favorites_list()
        flash("Favorite removed.", "success")
    except ValueError as error:
        if str(error) == "Favorite not found.":
            raise NotFoundError(str(error))
        flash(str(error), "error")

    if _is_htmx():
        return _render_favorites_list()
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/reorder", methods=["POST"])
@login_required
@require_household
def reorder(favorite_id):
    new_position = request.form.get("position", type=int)
    if new_position is None:
        flash("Invalid position.", "error")
        if _is_htmx():
            return _render_favorites_list()
        return redirect(url_for("favorites.index"))

    try:
        reorder_favorite(
            favorite_id,
            current_user.household_id,
            current_user.id,
            new_position,
        )
        if _is_htmx():
            return _render_favorites_list()
        flash("Favorite order updated.", "success")
    except ValueError as error:
        if str(error) == "Favorite not found.":
            raise NotFoundError(str(error))
        flash(str(error), "error")

    if _is_htmx():
        return _render_favorites_list()
    return redirect(url_for("favorites.index"))


@favorites_bp.route("/<int:favorite_id>/quick-add", methods=["POST"])
@login_required
@require_household
def quick_add(favorite_id):
    quantity_override = request.form.get("quantity_override")
    try:
        quick_add_from_favorite(
            favorite_id=favorite_id,
            household_id=current_user.household_id,
            user_id=current_user.id,
            quantity_override=quantity_override or None,
        )
        if _is_htmx():
            active_items, checked_items = get_grocery_list(current_user.household_id)
            return render_template(
                "favorites/_quick_add_feedback.html",
                success=True,
                message="Item added from favorite.",
                active_items=active_items,
                checked_items=checked_items,
            )
        flash("Item added from favorite.", "success")
    except ValueError as error:
        if str(error) == "Favorite not found.":
            raise NotFoundError(str(error))
        if _is_htmx():
            return render_template(
                "favorites/_quick_add_feedback.html",
                success=False,
                message=str(error),
            )
        flash(str(error), "error")

    return redirect(url_for("grocery.index"))
