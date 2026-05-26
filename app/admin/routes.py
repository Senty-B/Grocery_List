import logging

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user

from app.admin.forms import AdminLoginForm, CreateHouseholdForm, CreateUserForm
from app.admin.services import (
    admin_create_household_with_owner,
    admin_create_user,
    authenticate_admin,
    list_all_users,
    list_households_with_member_counts,
)
from app.common.authz import require_admin
from app.extensions import limiter
from app.models.household import Household

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


def _admin_login_rate_limit():
    return current_app.config.get(
        "ADMIN_LOGIN_RATE_LIMIT_PER_IP",
        "5 per minute; 20 per hour",
    )


def _is_admin_session():
    return current_user.is_authenticated and getattr(current_user, "is_admin", False)


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(_admin_login_rate_limit, methods=["POST"])
def login():
    if _is_admin_session():
        return redirect(url_for("admin.dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        admin, outcome = authenticate_admin(form.username.data, form.password.data)
        if outcome == "ok":
            logout_user()
            login_user(admin)
            logger.info(
                "Admin '%s' logged in from %s",
                admin.username,
                request.remote_addr,
            )
            return redirect(url_for("admin.dashboard"))

        if outcome == "locked":
            flash(
                "Account is temporarily locked. Try again later.",
                "error",
            )
        else:
            flash("Invalid username or password.", "error")

        logger.warning(
            "Failed admin login attempt for username='%s' outcome=%s from %s",
            form.username.data,
            outcome,
            request.remote_addr,
        )

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout", methods=["POST"])
@require_admin
def logout():
    logger.info("Admin '%s' logged out", current_user.username)
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@require_admin
def dashboard():
    households = list_households_with_member_counts()
    users = list_all_users()
    return render_template(
        "admin/dashboard.html",
        households=households,
        users=users,
    )


@admin_bp.route("/households/new", methods=["GET", "POST"])
@require_admin
def create_household():
    form = CreateHouseholdForm()
    if form.validate_on_submit():
        try:
            user = admin_create_household_with_owner(
                owner_username=form.owner_username.data,
                owner_password=form.owner_password.data,
                household_name=form.household_name.data,
            )
        except ValueError as error:
            flash(str(error), "error")
        else:
            logger.info(
                "Admin '%s' created household '%s' with owner '%s'",
                current_user.username,
                user.household.name,
                user.username,
            )
            flash(
                f"Household '{user.household.name}' created with owner '{user.username}'.",
                "success",
            )
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/create_household.html", form=form)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@require_admin
def create_user():
    form = CreateUserForm()
    households = Household.query.order_by(Household.name.asc()).all()
    form.household_id.choices = [(h.id, h.name) for h in households]

    if not households:
        flash("Create a household first.", "error")
        return redirect(url_for("admin.create_household"))

    if form.validate_on_submit():
        try:
            user = admin_create_user(
                username=form.username.data,
                password=form.password.data,
                household_id=form.household_id.data,
                role=form.role.data,
            )
        except ValueError as error:
            flash(str(error), "error")
        else:
            logger.info(
                "Admin '%s' created user '%s' (role=%s) in household %s",
                current_user.username,
                user.username,
                user.role,
                user.household_id,
            )
            flash(
                f"User '{user.username}' created in {user.household.name}.",
                "success",
            )
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/create_user.html", form=form)
