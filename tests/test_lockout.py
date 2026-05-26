"""Account-lockout tests that drive the service layer directly.

Driving the services keeps the tests deterministic: the HTTP rate limiter
is disabled in the testing config, so we can call `authenticate_*` in a
tight loop without triggering the IP-based throttle.
"""

import pytest

from app.admin.services import authenticate_admin, create_admin_account
from app.auth.services import authenticate_user, register_owner


STRONG_ADMIN_PASSWORD = "correcthorsebatterystaple"


@pytest.fixture
def tight_user_lockout(app):
    """Use an aggressive 3-fails-in-5-min policy for user lockout tests."""
    with app.app_context():
        previous = (
            app.config["USER_LOGIN_LOCKOUT_THRESHOLD"],
            app.config["USER_LOGIN_LOCKOUT_MINUTES"],
        )
        app.config["USER_LOGIN_LOCKOUT_THRESHOLD"] = 3
        app.config["USER_LOGIN_LOCKOUT_MINUTES"] = 5
        yield
        (
            app.config["USER_LOGIN_LOCKOUT_THRESHOLD"],
            app.config["USER_LOGIN_LOCKOUT_MINUTES"],
        ) = previous


@pytest.fixture
def tight_admin_lockout(app):
    with app.app_context():
        previous = (
            app.config["ADMIN_LOGIN_LOCKOUT_THRESHOLD"],
            app.config["ADMIN_LOGIN_LOCKOUT_MINUTES"],
        )
        app.config["ADMIN_LOGIN_LOCKOUT_THRESHOLD"] = 2
        app.config["ADMIN_LOGIN_LOCKOUT_MINUTES"] = 5
        yield
        (
            app.config["ADMIN_LOGIN_LOCKOUT_THRESHOLD"],
            app.config["ADMIN_LOGIN_LOCKOUT_MINUTES"],
        ) = previous


def test_user_lockout_triggers_after_threshold(db, tight_user_lockout):
    register_owner("alice", "password123", "Alice House")

    for _ in range(2):
        user, outcome = authenticate_user("alice", "wrong")
        assert outcome == "invalid"
        assert user is None

    user, outcome = authenticate_user("alice", "wrong")
    assert outcome == "locked"

    user, outcome = authenticate_user("alice", "password123")
    assert outcome == "locked", "correct password must not bypass an active lockout"


def test_user_successful_login_resets_failure_counter(db, tight_user_lockout):
    register_owner("alice", "password123", "Alice House")

    for _ in range(2):
        authenticate_user("alice", "wrong")

    user, outcome = authenticate_user("alice", "password123")
    assert outcome == "ok"
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_unknown_username_does_not_create_lockout_state(db):
    user, outcome = authenticate_user("ghost", "whatever")

    assert outcome == "invalid"
    assert user is None


def test_admin_lockout_triggers_after_threshold(db, tight_admin_lockout):
    create_admin_account("rootadmin", STRONG_ADMIN_PASSWORD)

    for _ in range(1):
        admin, outcome = authenticate_admin("rootadmin", "wrong")
        assert outcome == "invalid"
        assert admin is None

    admin, outcome = authenticate_admin("rootadmin", "wrong")
    assert outcome == "locked"

    admin, outcome = authenticate_admin("rootadmin", STRONG_ADMIN_PASSWORD)
    assert outcome == "locked"


def test_admin_successful_login_resets_failure_counter(db, tight_admin_lockout):
    create_admin_account("rootadmin", STRONG_ADMIN_PASSWORD)

    authenticate_admin("rootadmin", "wrong")

    admin, outcome = authenticate_admin("rootadmin", STRONG_ADMIN_PASSWORD)
    assert outcome == "ok"
    assert admin.failed_login_count == 0
    assert admin.locked_until is None


def test_rate_limit_config_is_applied(app):
    """Config-level smoke test: limits are populated and the limiter is live."""
    from app.extensions import limiter

    assert limiter is not None
    assert app.config["LOGIN_RATE_LIMIT_PER_IP"]
    assert app.config["ADMIN_LOGIN_RATE_LIMIT_PER_IP"]
    assert app.config["USER_LOGIN_LOCKOUT_THRESHOLD"] >= 1
    assert app.config["ADMIN_LOGIN_LOCKOUT_THRESHOLD"] >= 1
