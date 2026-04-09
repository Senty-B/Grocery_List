import logging

from sqlalchemy.exc import SQLAlchemyError

from app.common.utils import log_activity
from app.common.validators import (
    normalize_text,
    validate_note,
    validate_quantity,
    validate_unit,
    validate_item_name,
)
from app.extensions import db
from app.grocery.services import add_grocery_item
from app.models.favorite_item import FavoriteItem

logger = logging.getLogger(__name__)


def _ordered_favorites(household_id):
    return (
        FavoriteItem.query.filter_by(household_id=household_id)
        .order_by(FavoriteItem.sort_order, FavoriteItem.id)
        .all()
    )


def _normalize_sort_orders(favorites):
    for index, favorite in enumerate(favorites, start=1):
        favorite.sort_order = index


def add_favorite(household_id, user_id, name, quantity=1, unit=None, note=None):
    """Add a new household favorite."""
    name = validate_item_name(name)
    quantity = validate_quantity(quantity)
    unit = validate_unit(unit)
    note = validate_note(note)
    normalized_name = normalize_text(name)

    existing = FavoriteItem.query.filter_by(
        household_id=household_id,
        normalized_name=normalized_name,
    ).first()
    if existing:
        raise ValueError("This item is already a favorite.")

    max_order = (
        db.session.query(db.func.max(FavoriteItem.sort_order))
        .filter_by(household_id=household_id)
        .scalar()
    ) or 0

    favorite = FavoriteItem(
        household_id=household_id,
        name=name,
        normalized_name=normalized_name,
        default_quantity_value=quantity,
        default_unit=unit,
        default_note=note,
        sort_order=max_order + 1,
    )

    try:
        db.session.add(favorite)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception("Failed to add favorite '%s' for household %s", name, household_id)
        raise ValueError("Could not save favorite right now.") from error

    logger.info("Favorite added: '%s' for household %s", favorite.name, household_id)
    log_activity(
        household_id=household_id,
        user_id=user_id,
        action_type="add_favorite",
        entity_type="favorite_item",
        entity_id=favorite.id,
        payload={"name": favorite.name},
    )
    return favorite


def remove_favorite(favorite_id, household_id, user_id):
    """Delete a favorite and compact the remaining sort order."""
    favorite = FavoriteItem.query.filter_by(
        id=favorite_id,
        household_id=household_id,
    ).first()
    if not favorite:
        raise ValueError("Favorite not found.")

    try:
        db.session.delete(favorite)
        db.session.flush()
        remaining = _ordered_favorites(household_id)
        _normalize_sort_orders(remaining)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception(
            "Failed to remove favorite %s for household %s",
            favorite_id,
            household_id,
        )
        raise ValueError("Could not remove favorite right now.") from error

    logger.info("Favorite %s removed for household %s", favorite_id, household_id)
    log_activity(
        household_id=household_id,
        user_id=user_id,
        action_type="remove_favorite",
        entity_type="favorite_item",
        entity_id=favorite_id,
    )


def reorder_favorite(favorite_id, household_id, user_id, new_position):
    """Move a favorite to a new 1-based position and re-sequence sort_order."""
    favorites = _ordered_favorites(household_id)
    favorite = next((item for item in favorites if item.id == favorite_id), None)
    if not favorite:
        raise ValueError("Favorite not found.")
    if not favorites:
        raise ValueError("No favorites available.")

    bounded_position = max(1, min(new_position, len(favorites)))
    favorites = [item for item in favorites if item.id != favorite_id]
    favorites.insert(bounded_position - 1, favorite)
    _normalize_sort_orders(favorites)

    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception(
            "Failed to reorder favorite %s for household %s",
            favorite_id,
            household_id,
        )
        raise ValueError("Could not reorder favorites right now.") from error

    logger.info(
        "Favorite %s moved to position %s for household %s",
        favorite_id,
        bounded_position,
        household_id,
    )
    log_activity(
        household_id=household_id,
        user_id=user_id,
        action_type="reorder_favorite",
        entity_type="favorite_item",
        entity_id=favorite_id,
        payload={"position": bounded_position},
    )
    return favorite


def quick_add_from_favorite(
    favorite_id,
    household_id,
    user_id,
    quantity_override=None,
):
    """Add a grocery item using a favorite's defaults."""
    favorite = FavoriteItem.query.filter_by(
        id=favorite_id,
        household_id=household_id,
    ).first()
    if not favorite:
        raise ValueError("Favorite not found.")

    quantity = (
        validate_quantity(quantity_override)
        if quantity_override is not None
        else favorite.default_quantity_value
    )
    result = add_grocery_item(
        household_id=household_id,
        user_id=user_id,
        name=favorite.name,
        quantity=quantity,
        unit=favorite.default_unit,
        note=favorite.default_note,
    )
    log_activity(
        household_id=household_id,
        user_id=user_id,
        action_type="quick_add_favorite",
        entity_type="favorite_item",
        entity_id=favorite.id,
        payload={"grocery_item_id": result["id"]},
    )
    return result


def get_favorites_list(household_id):
    """Return all favorites ordered by sort_order."""
    return _ordered_favorites(household_id)
