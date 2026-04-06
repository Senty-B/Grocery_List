# Ticket 1: Project Structure & App Factory Setup

**Phase:** 1 — Foundation  
**Priority:** Critical  
**Dependencies:** None  
**Estimated effort:** Small

---

## Why This Matters

Every other ticket depends on this one. We are setting up the Flask application skeleton using the **app factory pattern**. This pattern means the app is created by a function (`create_app`) rather than as a global variable, which makes testing and configuration switching possible.

## What You Will Build

A runnable Flask project with the correct folder structure, configuration for three environments (development, testing, production), and lazy-loaded extensions.

---

## Tasks

### 1. Create the project root files

Create these files at the repository root:

`requirements.txt` — pin the core dependencies:

```text
Flask>=3.1,<4
Flask-Login>=0.6,<1
Flask-WTF>=1.2,<2
SQLAlchemy>=2.0,<3
Flask-SQLAlchemy>=3.1,<4
alembic>=1.13,<2
Flask-Migrate>=4.0,<5
psycopg[binary]>=3.1,<4
bcrypt>=4.1,<5
gunicorn>=22.0,<23
python-dotenv>=1.0,<2
```

`.flaskenv` — tells `flask run` which file to use:

```text
FLASK_APP=wsgi.py
FLASK_DEBUG=1
```

`.env.example` — template for local development secrets:

```text
SECRET_KEY=dev-secret-change-me
DATABASE_URL=postgresql+psycopg://grocery:grocery@localhost:5432/grocery_dev
LOG_LEVEL=DEBUG
```

`.gitignore` — at minimum:

```text
__pycache__/
*.pyc
.env
.env.prod
*.db
node_modules/
.venv/
```

### 2. Create the `app/` package

`app/__init__.py` — the app factory:

```python
from flask import Flask
from app.config import config_map
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    _register_blueprints(app)
    _register_error_handlers(app)

    return app


def _register_blueprints(app):
    from app.auth.routes import auth_bp
    from app.household.routes import household_bp
    from app.grocery.routes import grocery_bp
    from app.favorites.routes import favorites_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/household")
    app.register_blueprint(grocery_bp, url_prefix="/grocery")
    app.register_blueprint(favorites_bp, url_prefix="/favorites")


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(e):
        return "Internal server error", 500
```

**What's happening here:**
- `create_app()` is a function that builds a fresh Flask app every time it's called.
- `config_name` lets us switch between dev/test/prod settings.
- Extensions (database, login, CSRF, migrations) are initialized lazily — they are created once globally but attached to the app here.
- Blueprints are Flask's way of grouping related routes into modules.

`app/config.py` — environment-specific settings:

```python
import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://grocery:grocery@localhost:5432/grocery_dev",
    )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://grocery:grocery@localhost:5432/grocery_test",
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
```

`app/extensions.py` — one place for all extension instances:

```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
migrate = Migrate()
```

**Why a separate extensions file?** Extensions need to exist before the app is created (so models can import `db`), but they can't be initialized without an app. This file creates the objects; `create_app()` attaches them to the app later.

### 3. Create the entry points

`wsgi.py`:

```python
import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))
```

`run.py` (convenient local runner):

```python
from wsgi import app

if __name__ == "__main__":
    app.run()
```

### 4. Create empty blueprint packages

Create these files so the app factory can import blueprints without errors. Each file just declares the blueprint and at least one placeholder route:

- `app/auth/__init__.py` (empty)
- `app/auth/routes.py` — minimal:
  ```python
  from flask import Blueprint
  auth_bp = Blueprint("auth", __name__)

  @auth_bp.route("/login")
  def login():
      return "Login page placeholder"
  ```
- `app/household/__init__.py` (empty)
- `app/household/routes.py` — same pattern, blueprint name `household`
- `app/grocery/__init__.py` (empty)
- `app/grocery/routes.py` — same pattern, blueprint name `grocery`
- `app/favorites/__init__.py` (empty)
- `app/favorites/routes.py` — same pattern, blueprint name `favorites`
- `app/common/__init__.py` (empty)

### 5. Create empty directories

- `app/templates/` (add a `.gitkeep` file inside)
- `app/static/css/` (add a `.gitkeep` file inside)
- `app/static/js/` (add a `.gitkeep` file inside)
- `migrations/` (will be populated by Alembic in Ticket 2)
- `tests/` (add `__init__.py`)
- `docker/` (add a `.gitkeep`)

### 6. Set up structured logging

Add to `app/__init__.py` inside `create_app()`, before returning `app`:

```python
import logging
log_level = app.config.get("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

---

## Acceptance Criteria

- [ ] `pip install -r requirements.txt` succeeds with no errors
- [ ] `flask run` starts the dev server without errors
- [ ] Visiting `http://localhost:5000/login` shows the placeholder text
- [ ] Visiting `http://localhost:5000/grocery` shows the placeholder text
- [ ] `create_app("testing")` returns an app with `TESTING=True`
- [ ] `.env.example` exists and contains all required env vars
- [ ] Folder structure matches the spec exactly
