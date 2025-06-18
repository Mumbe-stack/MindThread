from flask import Blueprint, request, jsonify
from models import Post, db
from datetime import datetime

post_bp = Blueprint('post_bp', __name__, url_prefix='/api/posts')


@post_bp.route("/", methods=["GET"])
def list_posts():
    posts = Post.query.all()
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
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "tags": post.tags,
        "user_id": post.user_id,
        "created_at": post.created_at.isoformat()
    }), 200


@post_bp.route("/", methods=["POST"])
def create_post():
    data = request.json

    if not all(k in data for k in ("title", "content", "user_id")):
        return jsonify({"error": "Missing required fields: title, content, user_id"}), 400

    existing = Post.query.filter_by(user_id=data["user_id"], title=data["title"]).first()
    if existing:
        return jsonify({"error": "Post with this title already exists for this user"}), 409

    new_post = Post(
        title=data["title"],
        content=data["content"],
        tags=data.get("tags"),
        user_id=data["user_id"],
        created_at=datetime.utcnow()
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify({
        "success": "Post created",
        "id": new_post.id,
        "title": new_post.title
    }), 201


@post_bp.route("/<int:id>", methods=["PUT"])
def update_post(id):
    post = Post.query.get_or_404(id)
    data = request.json

    old_data = {
        "title": post.title,
        "content": post.content,
        "tags": post.tags
    }

    post.title = data.get("title", post.title)
    post.content = data.get("content", post.content)
    post.tags = data.get("tags", post.tags)

    db.session.commit()

    return jsonify({
        "success": "Post updated",
        "old": old_data,
        "new": {
            "title": post.title,
            "content": post.content,
            "tags": post.tags
        }
    }), 200


@post_bp.route("/<int:id>", methods=["DELETE"])
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({
        "success": f"Post ID {id} deleted"
    }), 200

