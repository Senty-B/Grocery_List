from functools import wraps

from flask import abort, current_app, redirect, url_for
from flask_login import current_user

from app.common.exceptions import AuthorizationError


def _household_endpoint():
    for endpoint in ("household.setup", "household.index", "household"):
        if endpoint in current_app.view_functions:
            return endpoint
    return "auth.login"


def _is_admin(user):
    return bool(getattr(user, "is_admin", False))


def _redirect_admin_home():
    return redirect(url_for("admin.dashboard"))


def require_household(view_func):
    """Ensure the logged-in user belongs to a household.

    Admins do not have a household; bounce them to the admin dashboard
    instead of the user-facing household setup page.
    """

    @wraps(view_func)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if _is_admin(current_user):
            return _redirect_admin_home()
        if not getattr(current_user, "household_id", None):
            return redirect(url_for(_household_endpoint()))
        return view_func(*args, **kwargs)

    return decorated


def require_owner(view_func):
    """Ensure the logged-in user is a household owner."""

    @wraps(view_func)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if _is_admin(current_user):
            return _redirect_admin_home()
        if getattr(current_user, "role", None) != "owner":
            raise AuthorizationError("Owner access required.")
        return view_func(*args, **kwargs)

    return decorated


def require_active_user(view_func):
    """Ensure the logged-in user account is active."""

    @wraps(view_func)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_active:
            raise AuthorizationError("User account is inactive.")
        return view_func(*args, **kwargs)

    return decorated


def require_admin(view_func):
    """Gate admin-only pages. Returns 404 for everyone who is not an admin
    so the endpoint does not leak its existence to unauthenticated scanners."""

    @wraps(view_func)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not _is_admin(current_user):
            abort(404)
        if not getattr(current_user, "is_active", True):
            abort(404)
        return view_func(*args, **kwargs)

    return decorated
