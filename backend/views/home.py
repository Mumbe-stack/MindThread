from flask import Blueprint, jsonify

home_bp = Blueprint('home_bp', __name__)

@home_bp.route("/")
def index():
    return jsonify({"message": "Welcome to MindThread API"})

