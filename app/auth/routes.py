import logging
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import LoginForm
from app.auth.services import authenticate_user
from app.extensions import limiter

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


def _safe_next_page(next_page):
    if not next_page:
        return None
    parts = urlsplit(next_page)
    if parts.scheme or parts.netloc:
        return None
    return next_page


def _already_logged_in_redirect():
    if getattr(current_user, "is_admin", False):
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("grocery.index"))


def _login_rate_limit():
    """Resolve rate-limit from app config at request time."""
    return current_app.config.get(
        "LOGIN_RATE_LIMIT_PER_IP",
        "5 per minute; 30 per hour",
    )


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(_login_rate_limit, methods=["POST"])
def login():
    if current_user.is_authenticated:
        return _already_logged_in_redirect()

    form = LoginForm()
    if form.validate_on_submit():
        user, outcome = authenticate_user(form.username.data, form.password.data)
        if outcome == "ok":
            session.permanent = True
            login_user(user)
            logger.info("User '%s' logged in", user.username)
            next_page = _safe_next_page(request.args.get("next"))
            return redirect(next_page or url_for("grocery.index"))

        if outcome == "locked":
            flash(
                "Account is temporarily locked. Try again later.",
                "error",
            )
        else:
            flash("Invalid username or password.", "error")

        logger.warning(
            "Failed login attempt for username='%s' outcome=%s from %s",
            form.username.data,
            outcome,
            request.remote_addr,
        )

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    username = getattr(current_user, "username", "?")
    logger.info("User '%s' logged out", username)
    logout_user()
    return redirect(url_for("auth.login"))
