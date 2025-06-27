from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from models import db, Post, User
from .utils import block_check_required

post_bp = Blueprint('post_bp', __name__)


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

        posts_data = []
        for post in posts:
            # Get like information
            likes_count = 0
            liked_by_list = []
            
            if hasattr(post, 'liked_by') and post.liked_by:
                likes_count = len(post.liked_by)
                liked_by_list = [user.id for user in post.liked_by]

            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "tags": post.tags,
                "user_id": post.user_id,
                "created_at": post.created_at.isoformat(),
                "is_approved": post.is_approved,
                "is_flagged": post.is_flagged,
                "likes": likes_count,
                "liked_by": liked_by_list
            }
            posts_data.append(post_data)

        return jsonify(posts_data), 200

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

        # Get like information
        likes_count = 0
        liked_by_list = []
        
        if hasattr(post, 'liked_by') and post.liked_by:
            likes_count = len(post.liked_by)
            liked_by_list = [u.id for u in post.liked_by]

        return jsonify({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat(),
            "is_approved": post.is_approved,
            "is_flagged": post.is_flagged,
            "likes": likes_count,
            "liked_by": liked_by_list
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
            created_at=datetime.now(timezone.utc),
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


@post_bp.route("/<int:id>/like", methods=["POST"])
@jwt_required()
def like_post(id):
    """Toggle like on a post - authentication required"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get_or_404(id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user already liked this post
        if hasattr(post, 'liked_by') and user in post.liked_by:
            post.liked_by.remove(user)
            message = "Post unliked"
        else:
            if not hasattr(post, 'liked_by'):
                # Initialize the relationship if it doesn't exist
                post.liked_by = []
            post.liked_by.append(user)
            message = "Post liked"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "likes": len(post.liked_by) if hasattr(post, 'liked_by') else 0,
            "liked_by": [u.id for u in post.liked_by] if hasattr(post, 'liked_by') else []
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error toggling post like: {e}")
        return jsonify({"error": "Failed to toggle like"}), 500


@post_bp.route("/<int:id>/like", methods=["OPTIONS"])
def like_post_options(id):
    """Handle OPTIONS request for CORS"""
    return '', 204


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
        "is_approved": p.is_approved,
        "likes": len(p.liked_by) if hasattr(p, 'liked_by') and p.liked_by else 0
    } for p in flagged]), 200