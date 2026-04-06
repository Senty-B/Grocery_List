# Ticket 8: Testing — Unit & Integration Tests

**Phase:** 2 — Core Backend  
**Priority:** High  
**Dependencies:** Tickets 5, 6, 7  
**Estimated effort:** Medium–Large

---

## Why This Matters

Tests prove the app works correctly and prevent future changes from breaking existing behavior. Without tests, you're flying blind.

---

## Tasks

### 1. Set up the test infrastructure

`tests/conftest.py`:

```python
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(app, db):
    """Returns a test client logged in as a household owner."""
    from app.auth.services import register_owner
    with app.app_context():
        user = register_owner("testowner", "password123", "Test Household")
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            yield c, user
```

### 2. Write unit tests for validators

`tests/test_validators.py` — test every function in `app/common/validators.py`:

- `normalize_text` with whitespace, None, Unicode
- `validate_item_name` with valid names, empty, too long, special chars
- `validate_quantity` with valid numbers, zero, negative, non-numeric
- `validate_unit` and `validate_note` length limits
- `validate_username` and `validate_password` edge cases

### 3. Write unit tests for grocery services

`tests/test_grocery_services.py`:

- Adding a new item creates one row
- Adding the same item twice increments quantity (UPSERT test)
- Different unit/note combinations do NOT merge
- Toggle active → checked → active
- Confirm purchase deletes only checked items

### 4. Write integration tests for auth flow

`tests/test_auth.py`:

- Register creates household + owner
- Login with correct credentials succeeds
- Login with wrong password fails
- Join household with valid invite code succeeds
- Join household with invalid code fails
- 6th member join fails

### 5. Write integration tests for grocery flow

`tests/test_grocery_routes.py`:

- Add item via POST returns success
- Toggle item via POST changes status
- Confirm purchase via POST removes checked items
- Unauthenticated requests redirect to login
- Cross-household access returns 403 or 404

### 6. Write integration tests for favorites flow

`tests/test_favorites.py`:

- Add favorite succeeds
- Duplicate favorite rejected
- Delete favorite removes it
- Quick-add creates grocery item

### 7. Configure pytest

`pytest.ini` or `pyproject.toml`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

---

## Acceptance Criteria

- [ ] `pytest` runs all tests without errors
- [ ] All tests pass (green)
- [ ] Tests use an isolated test database (not the dev database)
- [ ] Each test function is independent (no test depends on another test's side effects)
- [ ] Coverage includes: validators, grocery UPSERT, auth flow, toggle, confirm, favorites
- [ ] At minimum 30+ test cases across all files
