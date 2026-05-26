"""Smoke tests for the admin area."""

import pytest

from app.admin.services import (
    admin_create_user,
    authenticate_admin,
    create_admin_account,
)
from app.auth.services import register_owner
from app.models.admin_user import AdminUser
from app.models.user import User


STRONG_PASSWORD = "correcthorsebatterystaple"


def test_create_admin_account_persists_and_authenticates(db):
    admin = create_admin_account("rootadmin", STRONG_PASSWORD)

    assert admin.id is not None
    assert AdminUser.query.count() == 1

    authenticated, outcome = authenticate_admin("rootadmin", STRONG_PASSWORD)
    assert outcome == "ok"
    assert authenticated is not None

    denied, outcome = authenticate_admin("rootadmin", "wrong")
    assert outcome == "invalid"
    assert denied is None


def test_create_admin_rejects_weak_password(db):
    with pytest.raises(ValueError, match="at least 16"):
        create_admin_account("weakadmin", "short123")


def test_admin_create_user_picks_role_and_household(db):
    create_admin_account("rootadmin", STRONG_PASSWORD)
    owner = register_owner("alice", "password123", "Alice House")

    created = admin_create_user(
        username="bob",
        password="password123",
        household_id=owner.household_id,
        role="member",
    )

    assert created.household_id == owner.household_id
    assert created.role == "member"

    promoted = admin_create_user(
        username="carol",
        password="password123",
        household_id=owner.household_id,
        role="owner",
    )
    assert promoted.role == "owner"


def test_admin_create_user_enforces_member_cap(db):
    create_admin_account("rootadmin", STRONG_PASSWORD)
    owner = register_owner("alice", "password123", "Alice House")

    for index in range(1, 5):
        admin_create_user(
            username=f"user{index}",
            password="password123",
            household_id=owner.household_id,
            role="member",
        )

    with pytest.raises(ValueError, match="limit of 5"):
        admin_create_user(
            username="overflow",
            password="password123",
            household_id=owner.household_id,
            role="member",
        )


def test_admin_area_returns_404_for_unauthenticated(client):
    for path in (
        "/grocery/admin/",
        "/grocery/admin/households/new",
        "/grocery/admin/users/new",
    ):
        response = client.get(path)
        assert response.status_code == 404, path


def test_admin_area_returns_404_for_regular_user(client, db):
    register_owner("alice", "password123", "Alice House")
    client.post(
        "/login",
        data={"username": "alice", "password": "password123"},
        follow_redirects=False,
    )

    response = client.get("/grocery/admin/")

    assert response.status_code == 404


def test_admin_login_page_is_publicly_reachable(client):
    response = client.get("/grocery/admin/login")

    assert response.status_code == 200


def test_admin_login_happy_path_redirects_to_dashboard(client, db):
    create_admin_account("rootadmin", STRONG_PASSWORD)

    response = client.post(
        "/grocery/admin/login",
        data={"username": "rootadmin", "password": STRONG_PASSWORD},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/grocery/admin/")


def test_admin_can_reach_dashboard_when_logged_in(admin_client):
    client, _admin = admin_client

    response = client.get("/grocery/admin/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Admin" in body


def test_admin_can_create_household_via_http(admin_client, db):
    client, _admin = admin_client

    response = client.post(
        "/grocery/admin/households/new",
        data={
            "household_name": "Test House",
            "owner_username": "alice",
            "owner_password": "password123",
            "owner_confirm_password": "password123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    created = User.query.filter_by(username="alice").first()
    assert created is not None
    assert created.role == "owner"


def test_admin_can_create_user_via_http(admin_client, db):
    client, _admin = admin_client
    owner = register_owner("alice", "password123", "Alice House")

    response = client.post(
        "/grocery/admin/users/new",
        data={
            "household_id": str(owner.household_id),
            "role": "member",
            "username": "bob",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    bob = User.query.filter_by(username="bob").first()
    assert bob is not None
    assert bob.household_id == owner.household_id
    assert bob.role == "member"
