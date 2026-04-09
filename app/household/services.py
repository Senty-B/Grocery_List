import logging

from sqlalchemy.exc import SQLAlchemyError

from app.common.utils import generate_invite_code, log_activity
from app.extensions import db
from app.models.household import Household
from app.models.user import User

logger = logging.getLogger(__name__)


def _generate_unique_invite_code(length=8, exclude_household_id=None):
    invite_code = generate_invite_code(length=length)
    while True:
        existing = Household.query.filter_by(invite_code=invite_code).first()
        if not existing or existing.id == exclude_household_id:
            return invite_code
        invite_code = generate_invite_code(length=length)


def get_household_info(household_id):
    """Return the household and its active members."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")

    members = (
        User.query.filter_by(household_id=household_id, is_active=True)
        .order_by(User.role.desc(), User.username.asc())
        .all()
    )
    return household, members


def rotate_invite_code(household_id, user_id=None):
    """Generate and persist a new unique invite code for the household."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")

    household.invite_code = _generate_unique_invite_code(
        exclude_household_id=household.id
    )

    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception("Failed to rotate invite code for household %s", household_id)
        raise ValueError("Could not rotate invite code right now.") from error

    logger.info("Invite code rotated for household %s", household_id)
    if user_id is not None:
        log_activity(
            household_id=household.id,
            user_id=user_id,
            action_type="rotate_invite_code",
            entity_type="household",
            entity_id=household.id,
            payload={"invite_code": household.invite_code},
        )
    return household.invite_code
