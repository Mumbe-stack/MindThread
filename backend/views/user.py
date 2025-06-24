from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User

user_bp = Blueprint('user_bp', __name__, url_prefix="/api/users")


@user_bp.route("/", methods=["GET"])
@jwt_required()
def fetch_all_users():
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin privileges required"}), 403

    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "is_admin": u.is_admin,
        "is_blocked": u.is_blocked,
        "created_at": u.created_at.isoformat()
    } for u in users]), 200


@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def fetch_user_by_id(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat(),
        "posts": [{"id": p.id, "title": p.title} for p in user.posts],
        "comments": [{"id": c.id, "content": c.content} for c in user.comments]
    }), 200


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User '{user.username}' deleted successfully."}), 200


@user_bp.route("/<int:user_id>/block", methods=["PATCH"])
@jwt_required()
def block_user(user_id):
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_blocked = not user.is_blocked
    db.session.commit()

    status = "blocked" if user.is_blocked else "unblocked"
    return jsonify({"message": f"User '{user.username}' has been {status}."}), 200


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def fetch_current_user():
    user = User.query.get(get_jwt_identity())

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat(),
        "posts": [{"id": p.id, "title": p.title} for p in user.posts],
        "comments": [{"id": c.id, "content": c.content} for c in user.comments]
    }), 200
