from collections.abc import Iterator

import pytest
from sqlalchemy import text

from app import create_app
from app.auth.services import register_owner
from app.extensions import db as _db

app = create_app("testing")

TRUNCATE_ALL = text(
    "TRUNCATE TABLE activity_log, grocery_item, favorite_item, users, household "
    "RESTART IDENTITY CASCADE"
)


def _reset_database():
    _db.session.rollback()
    _db.session.execute(TRUNCATE_ALL)
    _db.session.commit()
    _db.session.remove()


def pytest_configure(config):
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        _reset_database()


def pytest_unconfigure(config):
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(name="app", scope="session")
def app_fixture():
    return app


@pytest.fixture(autouse=True)
def isolate_database() -> Iterator[None]:
    with app.app_context():
        _reset_database()
    yield
    with app.app_context():
        _reset_database()


@pytest.fixture
def db(app) -> Iterator:
    with app.app_context():
        yield _db
        _db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(app, db):
    user = register_owner("testowner", "password123", "Test Household")
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
        db.session.refresh(user)
        yield client, user
