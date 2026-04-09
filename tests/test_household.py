from app.models.household import Household
from app.models.user import User


def register_owner(client, db, username="alice"):
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
    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
    household = db.session.get(Household, user.household_id)
    return user, household


def join_member(client, invite_code, username="bob"):
    return client.post(
        "/household/join",
        data={
            "username": username,
            "password": "password123",
            "confirm_password": "password123",
            "invite_code": invite_code,
        },
        follow_redirects=False,
    )


def test_owner_can_view_household_page_with_invite_code(client, db):
    owner, household = register_owner(client, db)

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert household.name in body
    assert household.invite_code in body


def test_member_can_view_household_page_without_invite_code(client, db):
    owner, household = register_owner(client, db)
    client.post("/logout", follow_redirects=False)
    join_member(client, household.invite_code, username="bob")

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert household.name in body
    assert household.invite_code not in body
    assert "owner only" in body.lower()


def test_owner_can_rotate_invite_code_and_old_code_stops_working(client, db):
    owner, household = register_owner(client, db)
    old_code = household.invite_code

    response = client.post("/household/rotate-code", follow_redirects=False)
    db.session.expire_all()
    rotated_household = db.session.get(Household, household.id)

    assert response.status_code == 302
    assert rotated_household.invite_code != old_code

    client.post("/logout", follow_redirects=False)
    failed_join = join_member(client, old_code, username="charlie",)
    assert failed_join.status_code == 200 or failed_join.status_code == 302
    charlie = db.session.execute(
        db.select(User).filter_by(username="charlie")
    ).scalar_one_or_none()
    assert charlie is None


def test_member_list_shows_all_active_members_with_roles(client, db):
    owner, household = register_owner(client, db)
    client.post("/logout", follow_redirects=False)
    join_member(client, household.invite_code, username="bob")
    client.post("/logout", follow_redirects=False)
    client.post(
        "/login",
        data={"username": "alice", "password": "password123"},
        follow_redirects=False,
    )

    response = client.get("/household/", follow_redirects=False)

    body = response.get_data(as_text=True)
    assert "alice" in body
    assert "bob" in body
    assert "owner" in body
    assert "member" in body


def test_require_owner_blocks_members_from_rotating_code(client, db):
    owner, household = register_owner(client, db)
    original_code = household.invite_code
    client.post("/logout", follow_redirects=False)
    join_member(client, original_code, username="bob")

    response = client.post("/household/rotate-code", follow_redirects=False)
    db.session.expire_all()
    unchanged_household = db.session.get(Household, household.id)

    assert response.status_code == 403
    assert unchanged_household.invite_code == original_code


def test_unauthenticated_household_page_redirects_to_login(client):
    response = client.get("/household/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
