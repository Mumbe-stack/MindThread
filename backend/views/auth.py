from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from datetime import datetime, timezone
from models import db, User, TokenBlocklist

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

# ✅ Register
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not all(k in data for k in ("username", "email", "password")):
        return jsonify({"error": "Missing fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    hashed_pw = generate_password_hash(data["password"])
    new_user = User(
        username=data["username"],
        email=data["email"],
        password_hash=hashed_pw  # ✅ Corrected field name
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "User registered successfully"}), 201


# ✅ Login
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):  # ✅ Corrected field
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)

    return jsonify({
        "success": True,
        "access_token": access_token,
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    }), 200


# ✅ Get current user info
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    return jsonify({
        "success": True,
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    }), 200


# ✅ Logout with token blocklisting
@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    now = datetime.now(timezone.utc)

    db.session.add(TokenBlocklist(jti=jti, created_at=now))
    db.session.commit()

    return jsonify({"success": True, "message": "Logged out successfully"}), 200
