import logging

import bcrypt
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.auth.lockout import is_locked, record_failure, record_success
from app.common.utils import log_activity
from app.common.validators import (
    validate_household_name,
    validate_password,
    validate_username,
)
from app.extensions import db
from app.models.household import Household
from app.models.user import User

logger = logging.getLogger(__name__)


def hash_password(plain_password):
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def check_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def register_owner(username, password, household_name):
    """Create a new household and owner account."""
    username = validate_username(username)
    password = validate_password(password)
    household_name = validate_household_name(household_name)

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    household = Household(name=household_name)
    user = User(
        household=household,
        username=username,
        password_hash=hash_password(password),
        role="owner",
    )

    try:
        db.session.add(household)
        db.session.add(user)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception("Failed to register owner '%s'", username)
        raise ValueError("Could not create account right now.") from error

    logger.info(
        "Registered owner '%s' for household '%s'",
        user.username,
        household.name,
    )
    log_activity(
        household_id=household.id,
        user_id=user.id,
        action_type="register_owner",
        entity_type="household",
        entity_id=household.id,
        payload={"username": user.username},
    )
    return user


def authenticate_user(username, password):
    """Validate credentials against the `users` table.

    Returns a tuple ``(user_or_none, outcome)`` where outcome is one of:
      * ``"ok"``      - credentials valid, user returned
      * ``"locked"``  - correct account but currently locked out
      * ``"invalid"`` - missing or wrong credentials
    """
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return None, "invalid"

    threshold = current_app.config.get("USER_LOGIN_LOCKOUT_THRESHOLD", 10)
    lockout_minutes = current_app.config.get("USER_LOGIN_LOCKOUT_MINUTES", 15)

    user = User.query.filter_by(username=username).first()
    if user is None:
        return None, "invalid"

    if is_locked(user):
        return None, "locked"

    if not user.is_active or not check_password(password, user.password_hash):
        record_failure(user, threshold, lockout_minutes)
        if is_locked(user):
            logger.warning("User '%s' locked out after repeated failures", username)
            return None, "locked"
        return None, "invalid"

    record_success(user)
    return user, "ok"
