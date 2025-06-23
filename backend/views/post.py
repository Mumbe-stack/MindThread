from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from io import BytesIO
from datetime import datetime
from models import db, Post, User
from .utils import block_check_required  

post_bp = Blueprint('post_bp', __name__, url_prefix="/api/posts")


@post_bp.route("/", methods=["GET"])
@jwt_required(optional=True)
def list_posts():
    posts = Post.query.filter_by(is_approved=True).all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "tags": p.tags,
            "user_id": p.user_id,
            "created_at": p.created_at.isoformat()
        } for p in posts
    ]), 200


@post_bp.route("/<int:id>", methods=["GET"])
@jwt_required(optional=True)
def get_post(id):
    post = Post.query.get_or_404(id)
    current_user = get_jwt_identity()

    if not post.is_approved:
        if not current_user:
            return jsonify({}), 404
        user = User.query.get(current_user)
        if not user or not user.is_admin:
            return jsonify({}), 404

    return jsonify({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "tags": post.tags,
        "user_id": post.user_id,
        "created_at": post.created_at.isoformat()
    }), 200


@post_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required 
def create_post():
    data = request.get_json()
    user_id = get_jwt_identity()

    if not all(k in data for k in ("title", "content")):
        return jsonify({"error": "Missing required fields"}), 400

    existing = Post.query.filter_by(user_id=user_id, title=data["title"]).first()
    if existing:
        return jsonify({"error": "Post title already used"}), 409

    new_post = Post(
        title=data["title"],
        content=data["content"],
        tags=data.get("tags"),
        user_id=user_id
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify({"success": "Post created", "post_id": new_post.id}), 201


@post_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
@block_check_required 
def update_post(id):
    post = Post.query.get_or_404(id)
    user_id = get_jwt_identity()

    if post.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    post.title = data.get("title", post.title)
    post.content = data.get("content", post.content)
    post.tags = data.get("tags", post.tags)
    db.session.commit()

    return jsonify({"success": "Post updated"}), 200


@post_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required  
def delete_post(id):
    post = Post.query.get_or_404(id)
    user_id = get_jwt_identity()

    if post.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({"success": f"Post ID {id} deleted"}), 200


@post_bp.route("/<int:id>/like", methods=["PATCH"])
@jwt_required()
@block_check_required  
def like_post(id):
    post = Post.query.get_or_404(id)
    user = User.query.get(get_jwt_identity())

    if post in user.liked_posts:
        return jsonify({"error": "You already liked this post"}), 400

    user.liked_posts.append(post)
    db.session.commit()

    return jsonify({
        "message": f"Post ID {id} liked",
        "liked_by": {"id": user.id, "username": user.username}
    }), 200


@post_bp.route("/<int:id>/unlike", methods=["PATCH"])
@jwt_required()
@block_check_required 
def unlike_post(id):
    post = Post.query.get_or_404(id)
    user = User.query.get(get_jwt_identity())

    if post not in user.liked_posts:
        return jsonify({"error": "You haven't liked this post yet"}), 400

    user.liked_posts.remove(post)
    db.session.commit()

    return jsonify({
        "message": f"Post ID {id} unliked",
        "unliked_by": {"id": user.id, "username": user.username}
    }), 200


def to_dict(self):
    return {
        "id": self.id,
        "title": self.title,
        "content": self.content,
        "tags": self.tags,
        "created_at": self.created_at.isoformat(),
        "user_id": self.user_id,
        "is_approved": self.is_approved,
        "is_flagged": self.is_flagged
    }
