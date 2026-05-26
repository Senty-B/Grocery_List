"""Household page tests.

Invite-code self-join was removed; member creation now goes through the
admin area. These tests exercise what's left of the household view.
"""

from app.admin.services import admin_create_user
from app.auth.services import register_owner
from app.models.household import Household


def _login(client, username, password="password123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def _seed_household(username="alice"):
    owner = register_owner(username, "password123", f"{username} House")
    household = Household.query.get(owner.household_id)
    return owner, household


def test_owner_can_view_household_page(client, db):
    owner, household = _seed_household()
    _login(client, owner.username)

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert household.name in body
    assert owner.username in body


def test_member_can_view_household_page(client, db):
    owner, household = _seed_household()
    admin_create_user(
        username="bob",
        password="password123",
        household_id=household.id,
        role="member",
    )
    _login(client, "bob")

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert household.name in body
    assert "bob" in body


def test_member_list_shows_all_active_members_with_roles(client, db):
    owner, household = _seed_household()
    admin_create_user(
        username="bob",
        password="password123",
        household_id=household.id,
        role="member",
    )
    _login(client, owner.username)

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert "alice" in body
    assert "bob" in body
    assert "Owner" in body
    assert "Member" in body


def test_unauthenticated_household_page_redirects_to_login(client):
    response = client.get("/household/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_household_has_no_invite_code_attribute(db):
    _, household = _seed_household()

    assert not hasattr(household, "invite_code")


def test_rotate_code_endpoint_is_gone(client, db):
    owner, _ = _seed_household()
    _login(client, owner.username)

    response = client.post("/household/rotate-code", follow_redirects=False)

    assert response.status_code in (404, 405)
