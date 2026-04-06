from flask import Blueprint

grocery_bp = Blueprint("grocery", __name__)


@grocery_bp.route("/")
def index():
    return "Grocery page placeholder"
