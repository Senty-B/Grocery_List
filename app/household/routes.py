import logging

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user

from app.auth.forms import JoinHouseholdForm
from app.auth.services import join_household
from app.common.authz import require_household, require_owner
from app.household.services import get_household_info, rotate_invite_code

logger = logging.getLogger(__name__)
household_bp = Blueprint("household", __name__)


@household_bp.route("/")
@login_required
@require_household
def index():
    try:
        household, members = get_household_info(current_user.household_id)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("grocery.index"))

    return render_template(
        "household/index.html",
        household=household,
        members=members,
        is_owner=current_user.role == "owner",
    )


@household_bp.route("/join", methods=["POST"])
def join():
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
        except ValueError as error:
            flash(str(error), "error")
        else:
            login_user(user)
            flash("You've joined the household!", "success")
            return redirect(url_for("grocery.index"))

    return render_template("auth/join.html", form=form)


@household_bp.route("/rotate-code", methods=["POST"])
@login_required
@require_household
@require_owner
def rotate_code():
    try:
        new_code = rotate_invite_code(current_user.household_id, current_user.id)
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash(f"New invite code: {new_code}", "success")

    return redirect(url_for("household.index"))
