import logging

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.common.authz import require_household
from app.household.services import get_household_info

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
