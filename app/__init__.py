import logging
import os

from flask import Flask

from app.config import config_map
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401 — register models with SQLAlchemy

    migrate.init_app(app, db)

    _register_blueprints(app)
    _register_error_handlers(app)

    log_level = app.config.get("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return app


def _register_blueprints(app):
    from app.auth.routes import auth_bp
    from app.favorites.routes import favorites_bp
    from app.grocery.routes import grocery_bp
    from app.household.routes import household_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/household")
    app.register_blueprint(grocery_bp, url_prefix="/grocery")
    app.register_blueprint(favorites_bp, url_prefix="/favorites")


def _register_error_handlers(app):
    from app.common.exceptions import AppException

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        return error.message, error.status_code

    @app.errorhandler(404)
    def not_found(error):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(error):
        return "Internal server error", 500
