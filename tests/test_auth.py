from app.models.household import Household
from app.models.user import User


def register(client, username="alice", password="password123", household_name="My House"):
    return client.post(
        "/register",
        data={
            "username": username,
            "password": password,
            "confirm_password": password,
            "household_name": household_name,
        },
        follow_redirects=False,
    )


def login(client, username="alice", password="password123", follow_redirects=False):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=follow_redirects,
    )


def logout(client):
    return client.post("/logout", follow_redirects=False)


def join_household(
    client,
    invite_code,
    username="bob",
    password="password123",
    follow_redirects=False,
):
    return client.post(
        "/household/join",
        data={
            "username": username,
            "password": password,
            "confirm_password": password,
            "invite_code": invite_code,
        },
        follow_redirects=follow_redirects,
    )


def test_register_creates_household_and_owner(client, db):
    response = register(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/grocery/")

    user = db.session.execute(db.select(User).filter_by(username="alice")).scalar_one()
    household = db.session.get(Household, user.household_id)

    assert user.role == "owner"
    assert household.name == "My House"


def test_register_generates_household_invite_code(client, db):
    register(client)

    household = db.session.execute(db.select(Household)).scalar_one()

    assert household.invite_code
    assert len(household.invite_code) == 8
    assert household.invite_code.isalnum()


def test_login_with_correct_credentials_redirects_to_grocery(client):
    register(client)
    logout(client)

    response = login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/grocery/")


def test_login_with_wrong_password_shows_error(client):
    register(client)
    logout(client)

    response = login(client, password="wrong-password", follow_redirects=True)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Invalid username or password." in body


def test_join_household_with_valid_invite_code_succeeds(client, db):
    register(client)
    household = db.session.execute(db.select(Household)).scalar_one()
    logout(client)

    response = join_household(client, household.invite_code)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/grocery/")

    user = db.session.execute(db.select(User).filter_by(username="bob")).scalar_one()
    assert user.role == "member"
    assert user.household_id == household.id


def test_join_household_with_invalid_invite_code_fails(client, db):
    response = join_household(
        client,
        "INVALID1",
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    user = db.session.execute(
        db.select(User).filter_by(username="bob")
    ).scalar_one_or_none()

    assert response.status_code == 200
    assert "Invalid invite code." in body
    assert user is None


def test_sixth_member_join_is_rejected(client, db):
    register(client)
    household = db.session.execute(db.select(Household)).scalar_one()
    logout(client)

    for index in range(1, 5):
        response = join_household(client, household.invite_code, username=f"user{index}")
        assert response.status_code == 302
        logout(client)

    response = join_household(
        client,
        household.invite_code,
        username="user5",
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "maximum of 5 members" in body


def test_duplicate_username_is_rejected_on_register(client, db):
    register(client, username="sharedname")
    logout(client)

    response = register(client, username="sharedname")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Username is already taken." in body


def test_logout_redirects_to_login(client):
    register(client)

    response = logout(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
