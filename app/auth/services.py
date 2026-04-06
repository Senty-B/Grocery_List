import logging

import bcrypt
from sqlalchemy.exc import SQLAlchemyError

from app.common.utils import generate_invite_code, log_activity
from app.common.validators import (
    validate_household_name,
    validate_invite_code,
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


def _generate_unique_invite_code(length=8):
    invite_code = generate_invite_code(length=length)
    while Household.query.filter_by(invite_code=invite_code).first():
        invite_code = generate_invite_code(length=length)
    return invite_code


def register_owner(username, password, household_name):
    """Create a new household and owner account."""
    username = validate_username(username)
    password = validate_password(password)
    household_name = validate_household_name(household_name)

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    household = Household(
        name=household_name,
        invite_code=_generate_unique_invite_code(),
    )
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


def join_household(username, password, invite_code):
    """Create a member account and join an existing household."""
    username = validate_username(username)
    password = validate_password(password)
    invite_code = validate_invite_code(invite_code)

    household = Household.query.filter_by(invite_code=invite_code).first()
    if not household:
        raise ValueError("Invalid invite code.")

    active_member_count = User.query.filter_by(
        household_id=household.id,
        is_active=True,
    ).count()
    if active_member_count >= 5:
        raise ValueError("This household has reached the maximum of 5 members.")

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    user = User(
        household_id=household.id,
        username=username,
        password_hash=hash_password(password),
        role="member",
    )

    try:
        db.session.add(user)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception(
            "Failed to add user '%s' to household '%s'",
            username,
            household.name,
        )
        raise ValueError("Could not join household right now.") from error

    logger.info("User '%s' joined household '%s'", user.username, household.name)
    log_activity(
        household_id=household.id,
        user_id=user.id,
        action_type="join_household",
        entity_type="household",
        entity_id=household.id,
        payload={"username": user.username},
    )
    return user


def authenticate_user(username, password):
    """Verify credentials and return the active user when valid."""
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return None

    user = User.query.filter_by(username=username, is_active=True).first()
    if user and check_password(password, user.password_hash):
        return user
    return None
