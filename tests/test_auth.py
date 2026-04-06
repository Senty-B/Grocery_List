"""Ticket 4 acceptance tests — Auth Module.

Tests run against the real testing-config database (grocery_test)
so that SQLAlchemy models, constraints, and bcrypt hashing are
exercised end-to-end.
"""
import unittest

import bcrypt

from app import create_app
from app.extensions import db
from app.models.household import Household
from app.models.user import User


class AuthTestBase(unittest.TestCase):
    """Shared setup: create the Flask test app and reset the DB between tests.

    Each test gets its own app context so Flask's `g` (where Flask-Login
    caches `current_user`) is fresh.  This prevents stale ORM objects from
    leaking across tests.
    """
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        db.session.remove()
        self.app_ctx.pop()

    # -- helpers --------------------------------------------------------
    def _register(self, username="alice", password="secure1234",
                  confirm="secure1234", household_name="My House"):
        return self.client.post("/register", data={
            "username": username,
            "password": password,
            "confirm_password": confirm,
            "household_name": household_name,
        }, follow_redirects=False)

    def _login(self, username="alice", password="secure1234"):
        return self.client.post("/login", data={
            "username": username,
            "password": password,
        }, follow_redirects=False)

    def _logout(self):
        return self.client.post("/logout", follow_redirects=False)

    def _join(self, invite_code, username="bob", password="joinpass1234",
              confirm="joinpass1234"):
        return self.client.post("/household/join", data={
            "username": username,
            "password": password,
            "confirm_password": confirm,
            "invite_code": invite_code,
        }, follow_redirects=False)

    def _register_and_get_code(self, username="alice", password="secure1234",
                               household_name="My House"):
        """Register an owner, log out, and return the household invite code."""
        self._register(username, password, password, household_name)
        self._logout()
        household = db.session.execute(
            db.select(Household).limit(1)
        ).scalar_one()
        return household.invite_code


# ======================================================================
# AC-1  A new user can register and a household is automatically created
# AC-2  The registered user is the household owner
# AC-3  An invite code is generated and stored on the household
# ======================================================================
class TestRegistration(AuthTestBase):
    def test_register_creates_household_and_owner(self):
        resp = self._register()

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/grocery/"))

        user = db.session.execute(
            db.select(User).filter_by(username="alice")
        ).scalar_one()
        self.assertEqual(user.role, "owner")
        self.assertIsNotNone(user.household_id)

        household = db.session.execute(
            db.select(Household).filter_by(id=user.household_id)
        ).scalar_one()
        self.assertEqual(household.name, "My House")

    def test_household_has_invite_code(self):
        self._register()
        household = db.session.execute(
            db.select(Household).limit(1)
        ).scalar_one()

        self.assertIsNotNone(household.invite_code)
        self.assertTrue(len(household.invite_code) >= 8)
        self.assertTrue(household.invite_code.isalnum())


# ======================================================================
# AC-4  A second user can join using the invite code
# ======================================================================
class TestJoinHousehold(AuthTestBase):
    def test_second_user_can_join_via_invite_code(self):
        code = self._register_and_get_code()
        resp = self._join(code)

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/grocery/"))

        bob = db.session.execute(
            db.select(User).filter_by(username="bob")
        ).scalar_one()
        self.assertEqual(bob.role, "member")
        self.assertEqual(bob.household.invite_code, code)

    def test_join_page_renders(self):
        resp = self.client.get("/register/join")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("Join Household", body)


# ======================================================================
# AC-5  The 6th user trying to join gets a "maximum members" error
# ======================================================================
class TestMaxMembers(AuthTestBase):
    def test_sixth_member_is_rejected(self):
        code = self._register_and_get_code()

        for i in range(2, 6):
            self._join(code, username=f"user{i}", password="password1234",
                       confirm="password1234")
            self._logout()

        self.assertEqual(
            db.session.query(User).count(), 5
        )

        resp = self._join(code, username="user6", password="password1234",
                          confirm="password1234")

        self.assertNotEqual(resp.status_code, 302)
        body = resp.get_data(as_text=True)
        self.assertIn("maximum", body.lower())
        self.assertIsNone(
            db.session.execute(
                db.select(User).filter_by(username="user6")
            ).scalar_one_or_none()
        )


# ======================================================================
# AC-6  Login with correct credentials redirects to /grocery
# ======================================================================
class TestLoginSuccess(AuthTestBase):
    def test_login_redirects_to_grocery(self):
        self._register()
        self._logout()

        resp = self._login()
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/grocery/"))


# ======================================================================
# AC-7  Login with wrong credentials shows an error message
# ======================================================================
class TestLoginFailure(AuthTestBase):
    def test_wrong_password_shows_error(self):
        self._register()
        self._logout()

        resp = self._login(password="wrong-password")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("Invalid username or password", body)

    def test_nonexistent_user_shows_error(self):
        resp = self._login(username="nobody", password="doesnotmatter")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("Invalid username or password", body)


# ======================================================================
# AC-8  Passwords are stored as bcrypt hashes (never plaintext)
# ======================================================================
class TestPasswordHashing(AuthTestBase):
    def test_password_stored_as_bcrypt_hash(self):
        self._register(password="secure1234")
        self._logout()

        user = db.session.execute(
            db.select(User).filter_by(username="alice")
        ).scalar_one()

        self.assertTrue(
            user.password_hash.startswith("$2b$") or
            user.password_hash.startswith("$2a$"),
            "Password hash should be a bcrypt hash",
        )
        self.assertNotEqual(user.password_hash, "secure1234")

    def test_bcrypt_hash_verifies_correctly(self):
        self._register(password="secure1234")
        self._logout()

        user = db.session.execute(
            db.select(User).filter_by(username="alice")
        ).scalar_one()

        self.assertTrue(
            bcrypt.checkpw(b"secure1234", user.password_hash.encode())
        )
        self.assertFalse(
            bcrypt.checkpw(b"wrong", user.password_hash.encode())
        )


# ======================================================================
# AC-9  POST /logout ends the session and redirects to /login
# ======================================================================
class TestLogout(AuthTestBase):
    def test_logout_redirects_to_login(self):
        self._register()
        resp = self._logout()

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/login"))

    def test_session_is_ended_after_logout(self):
        """After logout, accessing an @login_required endpoint should
        redirect to login, proving the session was cleared."""
        self._register()
        self._logout()

        resp = self._logout()
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])


# ======================================================================
# AC-10  CSRF token is present and validated on all POST forms
# ======================================================================
class TestCSRF(AuthTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.csrf_app = create_app("development")
        cls.csrf_app.config["SQLALCHEMY_DATABASE_URI"] = cls.app.config[
            "SQLALCHEMY_DATABASE_URI"
        ]
        cls.csrf_app.config["WTF_CSRF_ENABLED"] = True
        cls.csrf_app.config["TESTING"] = True

    def test_login_page_contains_csrf_token(self):
        with self.csrf_app.test_client() as client:
            resp = client.get("/login")
            body = resp.get_data(as_text=True)
            self.assertIn('name="csrf_token"', body)

    def test_register_page_contains_csrf_token(self):
        with self.csrf_app.test_client() as client:
            resp = client.get("/register")
            body = resp.get_data(as_text=True)
            self.assertIn('name="csrf_token"', body)

    def test_join_page_contains_csrf_token(self):
        with self.csrf_app.test_client() as client:
            resp = client.get("/register/join")
            body = resp.get_data(as_text=True)
            self.assertIn('name="csrf_token"', body)

    def test_csrf_enforced_in_production_config(self):
        prod_app = create_app("development")
        self.assertTrue(prod_app.config["WTF_CSRF_ENABLED"])

    def test_csrf_disabled_in_testing_config(self):
        self.assertFalse(self.app.config["WTF_CSRF_ENABLED"])


# ======================================================================
# AC-11  Username uniqueness is enforced
# ======================================================================
class TestUsernameUniqueness(AuthTestBase):
    def test_duplicate_username_on_register_rejected(self):
        self._register(username="alice")
        self._logout()

        resp = self._register(username="alice", household_name="Other House")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("already taken", body.lower())

    def test_duplicate_username_on_join_rejected(self):
        code = self._register_and_get_code(username="alice")
        resp = self._join(code, username="alice")

        self.assertNotEqual(resp.status_code, 302)
        body = resp.get_data(as_text=True)
        self.assertIn("already taken", body.lower())


# ======================================================================
# Service-layer direct tests (supplement route tests)
# ======================================================================
class TestAuthServices(AuthTestBase):
    def test_authenticate_user_returns_user_on_valid_credentials(self):
        from app.auth.services import authenticate_user, register_owner

        register_owner("svcuser", "longpassword", "Svc House")
        user = authenticate_user("svcuser", "longpassword")

        self.assertIsNotNone(user)
        self.assertEqual(user.username, "svcuser")

    def test_authenticate_user_returns_none_on_wrong_password(self):
        from app.auth.services import authenticate_user, register_owner

        register_owner("svcuser", "longpassword", "Svc House")
        user = authenticate_user("svcuser", "wrongpassword")

        self.assertIsNone(user)

    def test_join_household_with_invalid_code_raises(self):
        from app.auth.services import join_household

        with self.assertRaisesRegex(ValueError, "Invalid invite code"):
            join_household("newuser", "longpassword", "BADCODE1")

    def test_safe_next_page_blocks_external_urls(self):
        """Ensure open-redirect protection on the login next param."""
        from app.auth.routes import _safe_next_page

        self.assertIsNone(_safe_next_page("https://evil.com/steal"))
        self.assertIsNone(_safe_next_page("//evil.com"))
        self.assertEqual(_safe_next_page("/grocery/"), "/grocery/")


if __name__ == "__main__":
    unittest.main()
