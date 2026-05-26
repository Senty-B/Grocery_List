import logging
import os

from flask import Flask, redirect, url_for
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import config_map
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])
    _configure_proxy_headers(app, config_name)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app import models  # noqa: F401 - register models with SQLAlchemy

    migrate.init_app(app, db)

    _register_blueprints(app)
    _register_health_route(app)
    _register_root_route(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_cli(app)

    log_level = app.config.get("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return app


def _configure_proxy_headers(app, config_name):
    if config_name == "production":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def _register_blueprints(app):
    from app.admin.routes import admin_bp
    from app.auth.routes import auth_bp
    from app.favorites.routes import favorites_bp
    from app.grocery.routes import grocery_bp
    from app.household.routes import household_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/household")
    app.register_blueprint(grocery_bp, url_prefix="/grocery")
    app.register_blueprint(favorites_bp, url_prefix="/favorites")
    app.register_blueprint(admin_bp, url_prefix="/grocery/admin")


def _register_cli(app):
    from app.admin.cli import admin_cli

    app.cli.add_command(admin_cli)


def _register_root_route(app):
    from flask_login import current_user

    @app.route("/")
    def root():
        if current_user.is_authenticated and getattr(current_user, "is_admin", False):
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("grocery.index"))


def _register_health_route(app):
    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            return "Database unreachable", 503
        return "OK", 200


def _register_security_headers(app):
    """Set defence-in-depth response headers on every response.

    These are layered on top of whatever the reverse proxy adds, so the
    app stays safe even if the Nginx config drifts.
    """

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        if not app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def _register_error_handlers(app):
    from app.common.exceptions import AppException

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        return error.message, error.status_code

    @app.errorhandler(404)
    def not_found(error):
        return "Page not found", 404

    @app.errorhandler(429)
    def too_many_requests(error):
        return (
            "Too many requests. Please wait a minute and try again.",
            429,
        )

    @app.errorhandler(500)
    def server_error(error):
        return "Internal server error", 500
