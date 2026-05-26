import logging

from app.extensions import db
from app.models.household import Household
from app.models.user import User

logger = logging.getLogger(__name__)


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
