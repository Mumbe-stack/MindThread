from flask import Blueprint, request, jsonify
from app.models import User, db

user_bp = Blueprint('user_bp', __name__)

@user_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    new_user = User(
        username=data["username"],
        email=data["email"],
        password_hash=data["password"]  
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": "User registered", "id": new_user.id}), 201

@user_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if user and user.password_hash == data["password"]:  
        return jsonify({"sucess": "Login successful", "user_id": user.id})
    return jsonify({"error": "Invalid credentials"}), 401

@user_bp.route("/<int:id>", methods=["GET"])
def user_profile(id):
    user = User.query.get_or_404(id)
    return jsonify({
        "username": user.username,
        "email": user.email,
        "posts": [p.title for p in user.posts],
        "comments": [c.content for c in user.comments]
    })
