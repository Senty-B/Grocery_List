from decimal import Decimal

from app.auth.services import register_owner
from app.grocery.services import (
    add_grocery_item,
    confirm_purchase,
    get_grocery_list,
    search_items,
    toggle_item_status,
)
from app.models.favorite_item import FavoriteItem
from app.models.grocery_item import GroceryItem


def create_owner(db, username="serviceowner"):
    user = register_owner(username, "password123", f"{username} House")
    db.session.refresh(user)
    return user


def household_items(db, household_id):
    return db.session.execute(
        db.select(GroceryItem)
        .filter_by(household_id=household_id)
        .order_by(GroceryItem.id)
    ).scalars().all()


def test_add_grocery_item_creates_one_row(db):
    user = create_owner(db)

    result = add_grocery_item(user.household_id, user.id, "Milk", quantity=2)
    items = household_items(db, user.household_id)

    assert result["status"] == "active"
    assert len(items) == 1
    assert items[0].quantity_value == Decimal("2")


def test_add_grocery_item_merges_duplicate_quantity(db):
    user = create_owner(db)

    add_grocery_item(user.household_id, user.id, "Milk", quantity=2)
    add_grocery_item(user.household_id, user.id, "Milk", quantity=3)
    items = household_items(db, user.household_id)

    assert len(items) == 1
    assert items[0].quantity_value == Decimal("5")


def test_add_grocery_item_does_not_merge_different_unit(db):
    user = create_owner(db)

    add_grocery_item(user.household_id, user.id, "Rice", quantity=1, unit="kg")
    add_grocery_item(user.household_id, user.id, "Rice", quantity=1, unit="bag")
    items = household_items(db, user.household_id)

    assert len(items) == 2


def test_add_grocery_item_does_not_merge_different_note(db):
    user = create_owner(db)

    add_grocery_item(user.household_id, user.id, "Milk", quantity=1, note="whole")
    add_grocery_item(user.household_id, user.id, "Milk", quantity=1, note="skim")
    items = household_items(db, user.household_id)

    assert len(items) == 2


def test_toggle_item_status_moves_active_to_checked_and_back(db):
    user = create_owner(db)
    add_grocery_item(user.household_id, user.id, "Bread")
    item = household_items(db, user.household_id)[0]

    toggle_item_status(item.id, user.household_id, user.id)
    db.session.expire_all()
    checked = db.session.get(GroceryItem, item.id)
    assert checked.status == "checked"
    assert checked.checked_by_user_id == user.id

    toggle_item_status(item.id, user.household_id, user.id)
    db.session.expire_all()
    active = db.session.get(GroceryItem, item.id)
    assert active.status == "active"
    assert active.checked_by_user_id is None


def test_toggle_item_status_merges_checked_item_back_into_existing_active_duplicate(db):
    user = create_owner(db)
    add_grocery_item(user.household_id, user.id, "Eggs", quantity=6)
    original = household_items(db, user.household_id)[0]
    toggle_item_status(original.id, user.household_id, user.id)
    add_grocery_item(user.household_id, user.id, "Eggs", quantity=12)

    merged_item = toggle_item_status(original.id, user.household_id, user.id)
    items = household_items(db, user.household_id)

    assert len(items) == 1
    assert merged_item.status == "active"
    assert items[0].quantity_value == Decimal("18")


def test_confirm_purchase_deletes_only_checked_items(db):
    user = create_owner(db)
    add_grocery_item(user.household_id, user.id, "Apples")
    add_grocery_item(user.household_id, user.id, "Bananas")
    items = household_items(db, user.household_id)
    apples = next(item for item in items if item.name == "Apples")
    toggle_item_status(apples.id, user.household_id, user.id)

    deleted_count = confirm_purchase(user.household_id)
    remaining_names = [item.name for item in household_items(db, user.household_id)]

    assert deleted_count == 1
    assert remaining_names == ["Bananas"]


def test_get_grocery_list_returns_active_then_checked(db):
    user = create_owner(db)
    add_grocery_item(user.household_id, user.id, "Milk")
    add_grocery_item(user.household_id, user.id, "Apples")
    apples = next(item for item in household_items(db, user.household_id) if item.name == "Apples")
    toggle_item_status(apples.id, user.household_id, user.id)

    active_items, checked_items = get_grocery_list(user.household_id)

    assert [item.name for item in active_items] == ["Milk"]
    assert [item.name for item in checked_items] == ["Apples"]


def test_search_items_returns_favorites_and_history(db):
    user = create_owner(db)
    db.session.add(
        FavoriteItem(
            household_id=user.household_id,
            name="Milk",
            normalized_name="milk",
            default_quantity_value=1,
            sort_order=1,
        )
    )
    db.session.commit()
    add_grocery_item(user.household_id, user.id, "Milky Way")

    results = search_items(user.household_id, "milk")

    assert [favorite.name for favorite in results["favorites"]] == ["Milk"]
    assert results["history"] == ["Milky Way"]
