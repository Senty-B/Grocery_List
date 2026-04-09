from decimal import Decimal

from app.models.favorite_item import FavoriteItem
from app.models.grocery_item import GroceryItem
from app.models.user import User


def create_authenticated_owner(client, db, username="alice"):
    client.post(
        "/register",
        data={
            "username": username,
            "password": "password123",
            "confirm_password": "password123",
            "household_name": f"{username} House",
        },
        follow_redirects=False,
    )
    return db.session.execute(db.select(User).filter_by(username=username)).scalar_one()


def add_item(client, name="Milk", quantity=1, unit="", note="", htmx=False):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        "/grocery/items",
        data={"name": name, "quantity": quantity, "unit": unit, "note": note},
        headers=headers,
        follow_redirects=False,
    )


def toggle_item(client, item_id, htmx=False):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        f"/grocery/items/{item_id}/toggle",
        headers=headers,
        follow_redirects=False,
    )


def confirm_purchase(client, htmx=False):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post("/grocery/confirm", headers=headers, follow_redirects=False)


def test_add_item_via_post_creates_grocery_row(client, db):
    user = create_authenticated_owner(client, db)

    response = add_item(client, "Milk")

    item = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalar_one()
    assert response.status_code == 302
    assert item.name == "Milk"
    assert item.status == "active"


def test_add_item_htmx_returns_list_fragment(client, db):
    create_authenticated_owner(client, db)

    response = add_item(client, "Bread", htmx=True)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Active Items" in body
    assert "Bread" in body


def test_toggle_item_changes_status(client, db):
    user = create_authenticated_owner(client, db)
    add_item(client, "Cheese")
    item = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalar_one()

    response = toggle_item(client, item.id)
    db.session.expire_all()
    item = db.session.get(GroceryItem, item.id)

    assert response.status_code == 302
    assert item.status == "checked"
    assert item.checked_by_user_id == user.id


def test_confirm_purchase_removes_only_checked_items(client, db):
    user = create_authenticated_owner(client, db)
    add_item(client, "Apples")
    add_item(client, "Bananas")
    items = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalars().all()
    apples = next(item for item in items if item.name == "Apples")
    toggle_item(client, apples.id)

    response = confirm_purchase(client)
    db.session.expire_all()
    remaining_names = {
        item.name
        for item in db.session.execute(
            db.select(GroceryItem).filter_by(household_id=user.household_id)
        ).scalars()
    }

    assert response.status_code == 302
    assert remaining_names == {"Bananas"}


def test_search_returns_matching_favorites_and_history(client, db):
    user = create_authenticated_owner(client, db)
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
    add_item(client, "Milky Way", quantity=1)

    response = client.get("/grocery/search?q=milk")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Favorite: Milk" in body
    assert "Recent: Milky Way" in body


def test_unauthenticated_grocery_requests_redirect_to_login(client):
    response = client.get("/grocery/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_add_item_redirects_to_login(client):
    response = client.post("/grocery/items", data={"name": "Milk"}, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_confirm_purchase_redirects_to_login(client):
    response = client.post("/grocery/confirm", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_cross_household_toggle_returns_not_found(client, db):
    owner_a = create_authenticated_owner(client, db, username="alice")
    add_item(client, "Secret Milk")
    item = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=owner_a.household_id)
    ).scalar_one()
    client.post("/logout", follow_redirects=False)

    create_authenticated_owner(client, db, username="bob")
    response = toggle_item(client, item.id)

    db.session.expire_all()
    unchanged = db.session.get(GroceryItem, item.id)
    assert response.status_code == 404
    assert unchanged.status == "active"


def test_confirm_purchase_htmx_returns_checked_fragment(client, db):
    user = create_authenticated_owner(client, db)
    add_item(client, "Crackers")
    item = db.session.execute(
        db.select(GroceryItem).filter_by(household_id=user.household_id)
    ).scalar_one()
    toggle_item(client, item.id)

    response = confirm_purchase(client, htmx=True)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No checked items." in body
