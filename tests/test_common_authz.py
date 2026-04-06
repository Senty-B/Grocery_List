import unittest

from flask import Blueprint, Flask
from flask_login import LoginManager, UserMixin, login_user

from app.common.authz import require_active_user, require_household, require_owner
from app.common.exceptions import AuthorizationError


class DummyUser(UserMixin):
    """Test user that decouples is_authenticated from is_active so both
    decorator branches can be exercised independently."""

    def __init__(self, user_id, household_id=None, role="member", active=True):
        self.id = str(user_id)
        self.household_id = household_id
        self.role = role
        self._active = active

    @property
    def is_active(self):
        return self._active

    @property
    def is_authenticated(self):
        return True


def create_test_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    login_manager = LoginManager()
    login_manager.init_app(app)

    users = {
        "member": DummyUser("member", household_id=1, role="member", active=True),
        "owner": DummyUser("owner", household_id=1, role="owner", active=True),
        "no_household": DummyUser(
            "no_household", household_id=None, role="member", active=True
        ),
        "inactive": DummyUser("inactive", household_id=1, role="member", active=False),
    }

    @login_manager.user_loader
    def load_user(user_id):
        return users.get(user_id)

    @app.errorhandler(AuthorizationError)
    def handle_auth_error(error):
        return error.message, error.status_code

    auth_bp = Blueprint("auth", __name__)
    household_bp = Blueprint("household", __name__)

    @auth_bp.route("/login")
    def login():
        return "login"

    @household_bp.route("/setup")
    def setup():
        return "household setup"

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/household")

    @app.route("/test-login/<user_id>")
    def test_login(user_id):
        login_user(users[user_id], force=True)
        return "ok"

    @app.route("/protected-household")
    @require_household
    def protected_household():
        return "protected"

    @app.route("/protected-owner")
    @require_owner
    def protected_owner():
        return "owner"

    @app.route("/protected-active")
    @require_active_user
    def protected_active():
        return "active"

    return app


class CommonAuthzTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()

    def test_require_household_redirects_unauthenticated_users(self):
        response = self.client.get("/protected-household")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_require_household_redirects_users_without_household_membership(self):
        self.client.get("/test-login/no_household")
        response = self.client.get("/protected-household")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/household/setup"))

    def test_require_owner_blocks_non_owners(self):
        self.client.get("/test-login/member")
        response = self.client.get("/protected-owner")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_data(as_text=True), "Owner access required.")

    def test_require_active_user_blocks_inactive_users(self):
        self.client.get("/test-login/inactive")
        response = self.client.get("/protected-active")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_data(as_text=True), "User account is inactive.")
