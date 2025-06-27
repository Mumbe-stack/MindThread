from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import db, User, Post, Comment

admin_bp = Blueprint("admin_bp", __name__) 


def admin_required(fn):
    @wraps(fn)  
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route("/health", methods=["GET"])
@admin_required
def health_check():
    return jsonify({"status": "Admin API healthy"}), 200

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch users"}), 500

@admin_bp.route("/users/<int:user_id>/block", methods=["PATCH"])
@admin_required
def toggle_block_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user.is_blocked = not user.is_blocked
        db.session.commit()
        return jsonify({
            "message": f"User {'blocked' if user.is_blocked else 'unblocked'} successfully.",
            "user_id": user.id,
            "is_blocked": user.is_blocked
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update user status"}), 500

@admin_bp.route("/flagged/posts", methods=["GET"])
@admin_required
def get_flagged_posts():
    try:
        posts = Post.query.filter_by(is_flagged=True).all()
        return jsonify([post.to_dict() for post in posts]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch flagged posts"}), 500

@admin_bp.route("/flagged/comments", methods=["GET"])
@admin_required
def get_flagged_comments():
    try:
        comments = Comment.query.filter_by(is_flagged=True).all()
        return jsonify([comment.to_dict() for comment in comments]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch flagged comments"}), 500

@admin_bp.route("/stats", methods=["GET"])  
@admin_required
def admin_stats():
    try:
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        blocked_users = User.query.filter_by(is_blocked=True).count()
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        
        return jsonify({
            "total_users": total_users,
            "total_posts": total_posts,
            "total_comments": total_comments,
            "blocked_users": blocked_users,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch admin stats"}), 500