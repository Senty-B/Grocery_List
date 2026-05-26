from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)


ADMIN_ID_PREFIX = "admin:"


@login_manager.user_loader
def load_user(user_id):
    """Dispatch to AdminUser for prefixed IDs, otherwise regular User."""
    from app.models.admin_user import AdminUser
    from app.models.user import User

    if user_id.startswith(ADMIN_ID_PREFIX):
        admin_pk = user_id.removeprefix(ADMIN_ID_PREFIX)
        if not admin_pk.isdigit():
            return None
        return db.session.get(AdminUser, int(admin_pk))

    if not user_id.isdigit():
        return None
    return db.session.get(User, int(user_id))
