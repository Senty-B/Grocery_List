"""HTTP tests for the public auth surface.

Public registration and household join routes were removed when account
creation moved behind the admin area. These tests verify that login/logout
still work and that the old registration endpoints no longer exist.
"""

from app.auth.services import register_owner


def seed_owner(username="alice", password="password123"):
    """Create an owner via the service layer so HTTP tests don't need /register."""
    return register_owner(username, password, f"{username} House")


def login(client, username="alice", password="password123", follow_redirects=False):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=follow_redirects,
    )


def logout(client):
    return client.post("/logout", follow_redirects=False)


def test_login_with_correct_credentials_redirects_to_grocery(client, db):
    seed_owner()

    response = login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/grocery/")


def test_login_with_wrong_password_shows_error(client, db):
    seed_owner()

    response = login(client, password="wrong-password", follow_redirects=True)

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Invalid username or password." in body


def test_logout_redirects_to_login(client, db):
    seed_owner()
    login(client)

    response = logout(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_public_register_endpoint_is_gone(client):
    response = client.post(
        "/register",
        data={
            "username": "new",
            "password": "password123",
            "confirm_password": "password123",
            "household_name": "Hacker House",
        },
        follow_redirects=False,
    )
    assert response.status_code in (404, 405)


def test_public_household_join_endpoint_is_gone(client):
    response = client.post(
        "/household/join",
        data={
            "username": "new",
            "password": "password123",
            "confirm_password": "password123",
            "invite_code": "ABCDEFGH",
        },
        follow_redirects=False,
    )
    assert response.status_code in (404, 405)


def test_landing_page_has_no_registration_links(client):
    response = client.get("/login")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "/register" not in body
    assert "/household/join" not in body
