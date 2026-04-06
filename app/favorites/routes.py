from flask import Blueprint

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/")
def index():
    return "Favorites page placeholder"
