from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, Post, User
from .utils import block_check_required

post_bp = Blueprint('post_bp', __name__, url_prefix="/api/posts")


@post_bp.route("", methods=["GET"])  
@jwt_required(optional=True)
def get_all_posts():
    """Get all posts - Modified for AdminDashboard compatibility"""
    try:
        current_user = get_jwt_identity()
        user = User.query.get(current_user) if current_user else None

        
        if user and user.is_admin:
            posts = Post.query.order_by(Post.created_at.desc()).all()
        else:
            posts = Post.query.filter_by(is_approved=True).order_by(Post.created_at.desc()).all()

        return jsonify([{
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat(),
            "is_approved": post.is_approved,
            "is_flagged": post.is_flagged
        } for post in posts]), 200

    except Exception as e:
        print("Error in get_all_posts:", e)
        return jsonify({"error": f"Failed to fetch posts: {str(e)}"}), 500


@post_bp.route("/<int:id>", methods=["GET"])
@jwt_required(optional=True)
def get_single_post(id):
    try:
        current_user = get_jwt_identity()
        user = User.query.get(current_user) if current_user else None

        post = Post.query.get_or_404(id)

        if not post.is_approved and (not user or not user.is_admin):
            return jsonify({"error": "Post not available"}), 403

        return jsonify({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat(),
            "is_approved": post.is_approved,
            "is_flagged": post.is_flagged
        }), 200

    except Exception as e:
        print("Error in get_single_post:", e)
        return jsonify({"error": "Failed to fetch post"}), 500


@post_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required
def create_post():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        tags = data.get("tags", "").strip()

        if not title or not content:
            return jsonify({"error": "Title and content are required"}), 400

        if len(title) > 200:
            return jsonify({"error": "Title must be under 200 characters"}), 400

        existing_post = Post.query.filter_by(user_id=user_id, title=title).first()
        if existing_post:
            return jsonify({"error": "You already have a post with this title"}), 409

        new_post = Post(
            title=title,
            content=content,
            tags=tags or None,
            user_id=user_id,
            created_at=datetime.utcnow(),
            is_approved=user.is_admin
        )

        db.session.add(new_post)
        db.session.commit()

        return jsonify({"success": True, "message": "Post created", "post_id": new_post.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create post"}), 500


@post_bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_post(id):
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        if post.user_id != user.id and not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            if len(title) > 200:
                return jsonify({"error": "Title too long"}), 400
            if Post.query.filter(Post.title == title, Post.user_id == post.user_id, Post.id != post.id).first():
                return jsonify({"error": "Duplicate title"}), 409
            post.title = title

        if "content" in data:
            content = data["content"].strip()
            if not content:
                return jsonify({"error": "Content cannot be empty"}), 400
            post.content = content

        if "tags" in data:
            post.tags = data["tags"].strip() or None

        db.session.commit()
        return jsonify({"success": True, "message": "Post updated"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update post"}), 500


@post_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_post(id):
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        if post.user_id != user.id and not user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403

        db.session.delete(post)
        db.session.commit()

        return jsonify({"success": True, "message": "Post deleted"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete post"}), 500


@post_bp.route("/<int:id>/like", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
@block_check_required
def like_post(id):
    if request.method == "OPTIONS":
        return '', 204

    user = User.query.get(get_jwt_identity())
    post = Post.query.get_or_404(id)

    if post in user.liked_posts:
        user.liked_posts.remove(post)
        msg = "Unliked"
    else:
        user.liked_posts.append(post)
        msg = "Liked"

    db.session.commit()
    return jsonify({"message": f"{msg} post '{post.title}'"}), 200


@post_bp.route("/<int:id>/approve", methods=["PATCH"])
@jwt_required()
def approve_post(id):
    user = User.query.get(get_jwt_identity())
    if not user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    post = Post.query.get_or_404(id)
    post.is_approved = not post.is_approved
    db.session.commit()

    return jsonify({"message": f"Post {'approved' if post.is_approved else 'disapproved'}"}), 200


@post_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
@block_check_required
def flag_post(id):
    post = Post.query.get_or_404(id)
    post.is_flagged = not post.is_flagged
    db.session.commit()
    return jsonify({"message": f"Post {'flagged' if post.is_flagged else 'unflagged'}"}), 200


@post_bp.route("/flagged", methods=["GET"])
@jwt_required()
def get_flagged_posts():
    user = User.query.get(get_jwt_identity())
    if not user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    flagged = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "content": p.content,
        "is_flagged": p.is_flagged,
        "is_approved": p.is_approved
    } for p in flagged]), 200
