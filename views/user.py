from flask import Blueprint, request, jsonify
from models import User, db
from werkzeug.security import generate_password_hash, check_password_hash

user_bp = Blueprint('user_bp', __name__, url_prefix="/api/users")

@user_bp.route('/', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@user_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not all(k in data for k in ("username", "email", "password")):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400

    hashed_password = generate_password_hash(data["password"])

    new_user = User(
        username=data["username"],
        email=data["email"],
        password_hash=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": "User registered", "id": new_user.id}), 201

@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data["email"]).first()

    if user and check_password_hash(user.password_hash, data["password"]):
        return jsonify({"success": "Login successful", "user_id": user.id}), 200

    return jsonify({"error": "Invalid credentials"}), 401

@user_bp.route("/<int:id>", methods=["GET"])
def user_profile(id):
    user = User.query.get_or_404(id)
    return jsonify({
        "username": user.username,
        "email": user.email,
        "posts": [p.title for p in user.posts],
        "comments": [c.content for c in user.comments]
    }), 200
