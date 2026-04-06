import logging
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import JoinHouseholdForm, LoginForm, RegistrationForm
from app.auth.services import authenticate_user, register_owner

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


def _safe_next_page(next_page):
    if not next_page:
        return None
    parts = urlsplit(next_page)
    if parts.scheme or parts.netloc:
        return None
    return next_page


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
            next_page = _safe_next_page(request.args.get("next"))
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
        except ValueError as error:
            flash(str(error), "error")
        else:
            login_user(user)
            flash("Account created! Welcome to your household.", "success")
            return redirect(url_for("grocery.index"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/register/join", methods=["GET"])
def register_join():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = JoinHouseholdForm()
    return render_template("auth/join.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logger.info("User '%s' logged out", current_user.username)
    logout_user()
    return redirect(url_for("auth.login"))
