from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Post, Comment

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

# --- Admin Access Decorator ---


def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# --- Routes ---


@admin_bp.route("/health", methods=["GET"])
@admin_required
def health_check():
    return jsonify({"status": "Admin API healthy"}), 200


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@admin_bp.route("/users/<int:user_id>/block", methods=["PATCH"])
@admin_required
def toggle_block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    db.session.commit()
    return jsonify({"message": f"User {'blocked' if user.is_blocked else 'unblocked'} successfully."}), 200


@admin_bp.route("/flagged/posts", methods=["GET"])
@admin_required
def get_flagged_posts():
    posts = Post.query.filter_by(is_flagged=True).all()
    return jsonify([post.to_dict() for post in posts]), 200


@admin_bp.route("/flagged/comments", methods=["GET"])
@admin_required
def get_flagged_comments():
    comments = Comment.query.filter_by(is_flagged=True).all()
    return jsonify([comment.to_dict() for comment in comments]), 200
