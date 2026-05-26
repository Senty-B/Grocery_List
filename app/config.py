import os
from datetime import timedelta


def _int_env(name, default):
    """Parse an integer env var, falling back to `default` on any error."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    WTF_CSRF_ENABLED = True
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    LOGIN_RATE_LIMIT_PER_IP = os.environ.get(
        "LOGIN_RATE_LIMIT_PER_IP",
        "5 per minute; 30 per hour",
    )
    ADMIN_LOGIN_RATE_LIMIT_PER_IP = os.environ.get(
        "ADMIN_LOGIN_RATE_LIMIT_PER_IP",
        "5 per minute; 20 per hour",
    )

    USER_LOGIN_LOCKOUT_THRESHOLD = _int_env("USER_LOGIN_LOCKOUT_THRESHOLD", 10)
    USER_LOGIN_LOCKOUT_MINUTES = _int_env("USER_LOGIN_LOCKOUT_MINUTES", 15)
    ADMIN_LOGIN_LOCKOUT_THRESHOLD = _int_env("ADMIN_LOGIN_LOCKOUT_THRESHOLD", 5)
    ADMIN_LOGIN_LOCKOUT_MINUTES = _int_env("ADMIN_LOGIN_LOCKOUT_MINUTES", 30)

    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")


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
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = (
        os.environ.get("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    )
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "https")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
