from decimal import Decimal

from app.auth.services import register_owner as _create_owner
from app.models.favorite_item import FavoriteItem
from app.models.grocery_item import GroceryItem
from app.models.user import User


def register_owner(client, db, username="alice"):
    _create_owner(username, "password123", f"{username} House")
    client.post(
        "/login",
        data={"username": username, "password": "password123"},
        follow_redirects=False,
    )
    return db.session.execute(db.select(User).filter_by(username=username)).scalar_one()


def add_favorite(client, name="Milk", quantity=1, unit="", note="", htmx=False):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        "/favorites",
        data={"name": name, "quantity": quantity, "unit": unit, "note": note},
        headers=headers,
        follow_redirects=False,
    )


def delete_favorite(client, favorite_id):
    return client.post(f"/favorites/{favorite_id}/delete", follow_redirects=False)


def reorder_favorite(client, favorite_id, position):
    return client.post(
        f"/favorites/{favorite_id}/reorder",
        data={"position": position},
        follow_redirects=False,
    )


def quick_add(client, favorite_id, quantity_override=None):
    data = {}
    if quantity_override is not None:
        data["quantity_override"] = quantity_override
    return client.post(
        f"/favorites/{favorite_id}/quick-add",
        data=data,
        follow_redirects=False,
    )


def test_add_favorite_succeeds(client, db):
    user = register_owner(client, db)

    response = add_favorite(client, "Bread", quantity=2, unit="loaf")
    favorite = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    assert response.status_code == 302
    assert favorite.name == "Bread"
    assert favorite.default_quantity_value == Decimal("2")


def test_duplicate_favorite_is_rejected(client, db):
    register_owner(client, db)
    add_favorite(client, "Milk")

    response = client.post(
        "/favorites",
        data={"name": "milk", "quantity": 1},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "This item is already a favorite." in body


def test_favorites_are_returned_in_sort_order(client, db):
    user = register_owner(client, db)
    add_favorite(client, "Cheese")
    add_favorite(client, "Apples")
    add_favorite(client, "Bread")

    favorites = db.session.execute(
        db.select(FavoriteItem)
        .filter_by(household_id=user.household_id)
        .order_by(FavoriteItem.sort_order)
    ).scalars().all()

    assert [favorite.name for favorite in favorites] == ["Cheese", "Apples", "Bread"]


def test_delete_favorite_removes_database_row(client, db):
    user = register_owner(client, db)
    add_favorite(client, "Eggs")
    favorite = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    response = delete_favorite(client, favorite.id)
    remaining = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=user.household_id)
    ).scalars().all()

    assert response.status_code == 302
    assert remaining == []


def test_quick_add_creates_grocery_item_using_favorite_defaults(client, db):
    user = register_owner(client, db)
    add_favorite(client, "Yogurt", quantity=3, unit="cups", note="Greek")
    favorite = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    response = quick_add(client, favorite.id)
    item = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    assert response.status_code == 302
    assert item.name == "Yogurt"
    assert item.quantity_value == Decimal("3")
    assert item.unit == "cups"
    assert item.note == "Greek"


def test_quick_add_uses_same_upsert_logic_as_grocery_add(client, db):
    user = register_owner(client, db)
    add_favorite(client, "Eggs", quantity=6)
    favorite = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    quick_add(client, favorite.id)
    quick_add(client, favorite.id)
    items = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalars().all()

    assert len(items) == 1
    assert items[0].quantity_value == Decimal("12")


def test_reorder_changes_sort_order_value(client, db):
    user = register_owner(client, db)
    add_favorite(client, "A")
    add_favorite(client, "B")
    add_favorite(client, "C")
    favorites = db.session.execute(
        db.select(FavoriteItem)
        .filter_by(household_id=user.household_id)
        .order_by(FavoriteItem.sort_order)
    ).scalars().all()
    favorite_c = next(favorite for favorite in favorites if favorite.name == "C")

    response = reorder_favorite(client, favorite_c.id, 1)
    reordered = db.session.execute(
        db.select(FavoriteItem)
        .filter_by(household_id=user.household_id)
        .order_by(FavoriteItem.sort_order)
    ).scalars().all()

    assert response.status_code == 302
    assert [favorite.name for favorite in reordered] == ["C", "A", "B"]


def test_all_favorites_routes_require_authentication(client):
    response = client.get("/favorites/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_create_favorite_redirects_to_login(client):
    response = client.post("/favorites", data={"name": "Milk"}, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_quick_add_redirects_to_login(client):
    response = client.post("/favorites/1/quick-add", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_cannot_access_other_households_favorites(client, db):
    owner_a = register_owner(client, db, username="alice")
    add_favorite(client, "Secret Favorite")
    favorite = db.session.execute(
        db.select(FavoriteItem).filter_by(household_id=owner_a.household_id)
    ).scalar_one()
    client.post("/logout", follow_redirects=False)

    register_owner(client, db, username="bob")
    response = delete_favorite(client, favorite.id)

    remaining = db.session.get(FavoriteItem, favorite.id)
    assert response.status_code == 404
    assert remaining is not None
