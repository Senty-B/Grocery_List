import logging
import secrets
import string

from app.extensions import db
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def generate_invite_code(length=8):
    """Generate a cryptographically secure uppercase alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def log_activity(
    household_id,
    user_id,
    action_type,
    entity_type,
    entity_id,
    payload=None,
):
    """Write an entry to the activity log table."""
    try:
        entry = ActivityLog(
            household_id=household_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception:
        logger.exception("Failed to write activity log")
        db.session.rollback()
        return None
