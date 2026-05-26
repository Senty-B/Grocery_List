import logging

from app.extensions import db
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


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
