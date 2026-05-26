import logging
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.lockout import is_locked, record_failure, record_success
from app.auth.services import check_password, hash_password
from app.common.validators import (
    validate_admin_password,
    validate_password,
    validate_username,
)
from app.extensions import db
from app.models.admin_user import AdminUser
from app.models.household import Household
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_HOUSEHOLD_MEMBERS = 5
VALID_USER_ROLES = ("owner", "member")


def create_admin_account(username, password):
    """Create a new admin account. Intended for CLI bootstrap."""
    username = validate_username(username)
    password = validate_admin_password(password)

    if AdminUser.query.filter_by(username=username).first():
        raise ValueError("Admin username is already taken.")

    admin = AdminUser(username=username, password_hash=hash_password(password))
    try:
        db.session.add(admin)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception("Failed to create admin '%s'", username)
        raise ValueError("Could not create admin right now.") from error

    logger.info("Admin '%s' created (id=%s)", admin.username, admin.id)
    return admin


def authenticate_admin(username, password):
    """Validate admin credentials with lockout support.

    Returns a tuple ``(admin_or_none, outcome)`` using the same outcome
    vocabulary as ``authenticate_user``: ``ok``, ``locked``, ``invalid``.
    """
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return None, "invalid"

    threshold = current_app.config.get("ADMIN_LOGIN_LOCKOUT_THRESHOLD", 5)
    lockout_minutes = current_app.config.get("ADMIN_LOGIN_LOCKOUT_MINUTES", 30)

    admin = AdminUser.query.filter_by(username=username).first()
    if admin is None:
        return None, "invalid"

    if is_locked(admin):
        return None, "locked"

    if not admin.is_active or not check_password(password, admin.password_hash):
        record_failure(admin, threshold, lockout_minutes)
        if is_locked(admin):
            logger.warning("Admin '%s' locked out after repeated failures", username)
            return None, "locked"
        return None, "invalid"

    record_success(admin)
    admin.last_login_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
    return admin, "ok"


def admin_create_household_with_owner(owner_username, owner_password, household_name):
    """Create a new household and an owner user inside it (admin-driven)."""
    from app.auth.services import register_owner

    return register_owner(owner_username, owner_password, household_name)


def admin_create_user(username, password, household_id, role):
    """Create a user inside an existing household. Admin picks the role."""
    username = validate_username(username)
    password = validate_password(password)

    if role not in VALID_USER_ROLES:
        raise ValueError("Role must be 'owner' or 'member'.")

    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")

    active_count = User.query.filter_by(
        household_id=household.id,
        is_active=True,
    ).count()
    if active_count >= MAX_HOUSEHOLD_MEMBERS:
        raise ValueError(
            f"Household has reached the limit of {MAX_HOUSEHOLD_MEMBERS} members."
        )

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    user = User(
        household_id=household.id,
        username=username,
        password_hash=hash_password(password),
        role=role,
    )

    try:
        db.session.add(user)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception(
            "Failed to admin-create user '%s' for household %s",
            username,
            household.id,
        )
        raise ValueError("Could not create user right now.") from error

    logger.info(
        "Admin-created user '%s' (role=%s) in household %s",
        user.username,
        user.role,
        household.id,
    )
    return user


def list_households_with_member_counts():
    """Return households with active member counts for the admin dashboard."""
    households = Household.query.order_by(Household.name.asc()).all()
    counts = {}
    for household in households:
        counts[household.id] = User.query.filter_by(
            household_id=household.id,
            is_active=True,
        ).count()
    return [(household, counts[household.id]) for household in households]


def list_all_users():
    """Return all users, grouped by household id (convenience for dashboard)."""
    return (
        User.query.order_by(User.household_id.asc(), User.role.desc(), User.username.asc())
        .all()
    )
