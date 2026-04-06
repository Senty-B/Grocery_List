from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user

from app.auth.forms import JoinHouseholdForm
from app.auth.services import join_household

household_bp = Blueprint("household", __name__)


@household_bp.route("/")
def index():
    return "Household page placeholder"


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
