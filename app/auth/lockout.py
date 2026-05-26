"""Shared account-lockout helpers for the User and AdminUser tables.

Both authenticator flows use the same three primitives so the lockout
policy stays in one place and both login surfaces behave consistently.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


def is_locked(account):
    """Return True while the account is inside an active lockout window."""
    locked_until = getattr(account, "locked_until", None)
    if not locked_until:
        return False
    return locked_until > datetime.now(timezone.utc)


def record_failure(account, threshold, lockout_minutes):
    """Increment the failure counter and open a lockout window once we hit
    the configured threshold. Safe to call even when `account` is None."""
    if account is None:
        return

    account.failed_login_count = (account.failed_login_count or 0) + 1
    if account.failed_login_count >= threshold:
        account.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=lockout_minutes,
        )
    _commit_silently()


def record_success(account):
    """Clear any accumulated failure state after a successful login."""
    account.failed_login_count = 0
    account.locked_until = None
    _commit_silently()


def _commit_silently():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
