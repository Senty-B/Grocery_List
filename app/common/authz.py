from functools import wraps

from flask import current_app, redirect, url_for
from flask_login import current_user

from app.common.exceptions import AuthorizationError


def _household_endpoint():
    for endpoint in ("household.setup", "household.index", "household"):
        if endpoint in current_app.view_functions:
            return endpoint
    return "auth.login"


def require_household(view_func):
    """Ensure the logged-in user belongs to a household."""

    @wraps(view_func)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
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
