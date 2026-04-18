import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.common.utils import log_activity
from app.common.validators import (
    normalize_text,
    validate_item_name,
    validate_note,
    validate_quantity,
    validate_unit,
)
from app.extensions import db
from app.grocery.recommendations import VEGETARIAN_RECOMMENDATIONS
from app.models.favorite_item import FavoriteItem
from app.models.grocery_item import GroceryItem

MAX_SUGGESTIONS_PER_GROUP = 5

logger = logging.getLogger(__name__)

UPSERT_GROCERY_ITEM_SQL = text(
    """
    INSERT INTO grocery_item (
        household_id,
        name,
        normalized_name,
        unit,
        normalized_unit,
        note,
        normalized_note,
        quantity_value,
        status,
        created_by_user_id,
        created_at,
        updated_at
    ) VALUES (
        :household_id,
        :name,
        :normalized_name,
        :unit,
        :normalized_unit,
        :note,
        :normalized_note,
        :quantity_value,
        'active',
        :created_by_user_id,
        NOW(),
        NOW()
    )
    ON CONFLICT (household_id, normalized_name, normalized_unit, normalized_note)
        WHERE status = 'active'
    DO UPDATE SET
        quantity_value = grocery_item.quantity_value + EXCLUDED.quantity_value,
        updated_at = NOW()
    RETURNING id, quantity_value, status
    """
)


def add_grocery_item(household_id, user_id, name, quantity=1, unit=None, note=None):
    """Add an item or atomically merge quantity into an active duplicate."""
    name = validate_item_name(name)
    quantity = validate_quantity(quantity)
    unit = validate_unit(unit)
    note = validate_note(note)

    payload = {
        "household_id": household_id,
        "name": name,
        "normalized_name": normalize_text(name),
        "unit": unit,
        "normalized_unit": normalize_text(unit),
        "note": note,
        "normalized_note": normalize_text(note),
        "quantity_value": quantity,
        "created_by_user_id": user_id,
    }

    try:
        result = db.session.execute(UPSERT_GROCERY_ITEM_SQL, payload).mappings().one()
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception(
            "Failed to upsert grocery item '%s' for household %s",
            name,
            household_id,
        )
        raise ValueError("Could not save grocery item right now.") from error

    logger.info(
        "Grocery item upserted: id=%s qty=%s household=%s",
        result["id"],
        result["quantity_value"],
        household_id,
    )
    log_activity(
        household_id=household_id,
        user_id=user_id,
        action_type="add_grocery_item",
        entity_type="grocery_item",
        entity_id=result["id"],
        payload={"quantity_value": str(result["quantity_value"])},
    )
    return dict(result)


def toggle_item_status(item_id, household_id, user_id):
    """Toggle a grocery item between active and checked within a household."""
    item = GroceryItem.query.filter_by(id=item_id, household_id=household_id).first()
    if not item:
        raise ValueError("Item not found.")

    try:
        if item.status == "active":
            item.status = "checked"
            item.checked_by_user_id = user_id
            item.checked_at = datetime.now(timezone.utc)
            db.session.commit()
            log_activity(
                household_id=household_id,
                user_id=user_id,
                action_type="check_grocery_item",
                entity_type="grocery_item",
                entity_id=item.id,
            )
            logger.info("Item %s toggled to checked", item.id)
            return item

        duplicate_active_item = GroceryItem.query.filter_by(
            household_id=household_id,
            status="active",
            normalized_name=item.normalized_name,
            normalized_unit=item.normalized_unit,
            normalized_note=item.normalized_note,
        ).first()

        if duplicate_active_item:
            duplicate_active_item.quantity_value = (
                duplicate_active_item.quantity_value + item.quantity_value
            )
            duplicate_active_item.updated_at = datetime.now(timezone.utc)
            db.session.delete(item)
            db.session.commit()
            log_activity(
                household_id=household_id,
                user_id=user_id,
                action_type="uncheck_grocery_item_merge",
                entity_type="grocery_item",
                entity_id=duplicate_active_item.id,
                payload={"merged_item_id": item_id},
            )
            logger.info(
                "Checked item %s merged back into active item %s",
                item_id,
                duplicate_active_item.id,
            )
            return duplicate_active_item

        item.status = "active"
        item.checked_by_user_id = None
        item.checked_at = None
        db.session.commit()
        log_activity(
            household_id=household_id,
            user_id=user_id,
            action_type="uncheck_grocery_item",
            entity_type="grocery_item",
            entity_id=item.id,
        )
        logger.info("Item %s toggled to active", item.id)
        return item
    except (IntegrityError, SQLAlchemyError) as error:
        db.session.rollback()
        logger.exception("Failed to toggle item %s for household %s", item_id, household_id)
        raise ValueError("Could not update item status right now.") from error


def confirm_purchase(household_id):
    """Delete all checked items for the household in one transaction."""
    checked_items = GroceryItem.query.filter_by(
        household_id=household_id,
        status="checked",
    ).all()
    deleted_count = len(checked_items)

    try:
        for item in checked_items:
            db.session.delete(item)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.exception("Failed to confirm purchase for household %s", household_id)
        raise ValueError("Could not confirm purchase right now.") from error

    logger.info(
        "Confirmed purchase for household %s: %s checked item(s) removed",
        household_id,
        deleted_count,
    )
    return deleted_count


def get_grocery_list(household_id):
    """Return active items first, then checked items, both alphabetically sorted."""
    active_items = (
        GroceryItem.query.filter_by(household_id=household_id, status="active")
        .order_by(GroceryItem.normalized_name, GroceryItem.name, GroceryItem.id)
        .all()
    )
    checked_items = (
        GroceryItem.query.filter_by(household_id=household_id, status="checked")
        .order_by(GroceryItem.normalized_name, GroceryItem.name, GroceryItem.id)
        .all()
    )
    return active_items, checked_items


def search_items(household_id, query):
    """Search favorites, past items, and default recommendations for suggestions."""
    normalized_query = normalize_text(query)
    empty_result = {"favorites": [], "history": [], "recommendations": []}
    if not normalized_query:
        return empty_result

    search_term = f"{normalized_query}%"
    favorites = (
        FavoriteItem.query.filter_by(household_id=household_id)
        .filter(FavoriteItem.normalized_name.ilike(search_term))
        .order_by(FavoriteItem.sort_order, FavoriteItem.name)
        .limit(MAX_SUGGESTIONS_PER_GROUP)
        .all()
    )

    matching_items = (
        GroceryItem.query.with_entities(GroceryItem.name, GroceryItem.normalized_name)
        .filter_by(household_id=household_id)
        .filter(GroceryItem.normalized_name.ilike(search_term))
        .order_by(GroceryItem.normalized_name, GroceryItem.name)
        .all()
    )

    seen_normalized = {normalize_text(favorite.name) for favorite in favorites}

    history = []
    for row in matching_items:
        if row.normalized_name in seen_normalized:
            continue
        seen_normalized.add(row.normalized_name)
        history.append(row.name)
        if len(history) >= MAX_SUGGESTIONS_PER_GROUP:
            break

    recommendations = _build_recommendations(normalized_query, seen_normalized)

    return {
        "favorites": favorites,
        "history": history,
        "recommendations": recommendations,
    }


def _build_recommendations(normalized_query, seen_normalized):
    """Filter curated recommendations by prefix match and skip duplicates."""
    recommendations = []
    for item in VEGETARIAN_RECOMMENDATIONS:
        normalized_item = normalize_text(item)
        if not normalized_item.startswith(normalized_query):
            continue
        if normalized_item in seen_normalized:
            continue
        seen_normalized.add(normalized_item)
        recommendations.append(item)
        if len(recommendations) >= MAX_SUGGESTIONS_PER_GROUP:
            break
    return recommendations
