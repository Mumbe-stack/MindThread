from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime, timezone
from models import db, Post, User, Comment, Vote
from .utils import block_check_required

post_bp = Blueprint('post_bp', __name__)

@post_bp.route("", methods=["GET"])  
@jwt_required(optional=True)
def get_all_posts():
    """Get all posts - users see only approved, admins see all"""
    try:
        # Get current user
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        # Filter posts based on user role
        if current_user and current_user.is_admin:
            posts = Post.query.order_by(Post.created_at.desc()).all()
        else:
            posts = Post.query.filter_by(is_approved=True).order_by(Post.created_at.desc()).all()

        posts_data = []
        for post in posts:
            # Get user's vote on this post if logged in
            user_vote = None
            if current_user_id:
                vote = Vote.query.filter_by(user_id=current_user_id, post_id=post.id).first()
                user_vote = vote.value if vote else None

            # Build post data with author username
            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "tags": post.tags,
                "user_id": post.user_id,
                "username": post.author.username if post.author else "Unknown User",
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                "is_approved": post.is_approved,
                "is_flagged": post.is_flagged,
                "likes_count": post.likes_count,
                "vote_score": post.vote_score,
                "upvotes_count": post.upvotes_count,
                "downvotes_count": post.downvotes_count,
                "comments_count": post.comments.filter_by(is_approved=True).count(),
                "user_vote": user_vote
            }
            posts_data.append(post_data)

        return jsonify(posts_data), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_all_posts: {e}")
        return jsonify({"error": f"Failed to fetch posts: {str(e)}"}), 500

@post_bp.route("/<int:id>", methods=["GET"])
@jwt_required(optional=True)
def get_single_post(id):
    """Get a single post with comments"""
    try:
        # Get current user
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        post = Post.query.get_or_404(id)

        # Check if user can view this post
        if not post.is_approved and (not current_user or not current_user.is_admin):
            return jsonify({"error": "Post not available"}), 403

        # Get user's vote on this post if logged in
        user_vote = None
        if current_user_id:
            vote = Vote.query.filter_by(user_id=current_user_id, post_id=post.id).first()
            user_vote = vote.value if vote else None

        # Get approved comments (or all for admin)
        if current_user and current_user.is_admin:
            comments = post.comments.order_by(Comment.created_at.asc()).all()
        else:
            comments = post.comments.filter_by(is_approved=True).order_by(Comment.created_at.asc()).all()

        # Build comments data
        comments_data = []
        for comment in comments:
            comment_user_vote = None
            if current_user_id:
                vote = Vote.query.filter_by(user_id=current_user_id, comment_id=comment.id).first()
                comment_user_vote = vote.value if vote else None

            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "user_id": comment.user_id,
                "username": comment.author.username if comment.author else "Unknown User",
                "parent_id": comment.parent_id,
                "created_at": comment.created_at.isoformat(),
                "is_approved": comment.is_approved,
                "is_flagged": comment.is_flagged,
                "likes_count": comment.likes_count,
                "vote_score": comment.vote_score,
                "upvotes_count": comment.upvotes_count,
                "downvotes_count": comment.downvotes_count,
                "user_vote": comment_user_vote
            }
            comments_data.append(comment_data)

        post_data = {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "user_id": post.user_id,
            "username": post.author.username if post.author else "Unknown User",
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
            "is_approved": post.is_approved,
            "is_flagged": post.is_flagged,
            "likes_count": post.likes_count,
            "vote_score": post.vote_score,
            "upvotes_count": post.upvotes_count,
            "downvotes_count": post.downvotes_count,
            "user_vote": user_vote,
            "comments": comments_data
        }

        return jsonify(post_data), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_single_post: {e}")
        return jsonify({"error": "Failed to fetch post"}), 500

@post_bp.route("", methods=["POST"])
@jwt_required()
@block_check_required
def create_post():
    """Create a new post"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400

        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        tags = data.get("tags", "").strip()

        if not title or not content:
            return jsonify({"error": "Title and content are required"}), 400

        if len(title) > 200:
            return jsonify({"error": "Title must be under 200 characters"}), 400

        # Check for duplicate title by same user
        existing_post = Post.query.filter_by(user_id=user_id, title=title).first()
        if existing_post:
            return jsonify({"error": "You already have a post with this title"}), 409

        # Auto-approve for admins, pending for regular users
        new_post = Post(
            title=title,
            content=content,
            tags=tags or None,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            is_approved=user.is_admin,  # Auto-approve admin posts
            is_flagged=False
        )

        db.session.add(new_post)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post created successfully" + (" and approved" if user.is_admin else " - pending approval"),
            "post_id": new_post.id,
            "is_approved": new_post.is_approved
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating post: {e}")
        return jsonify({"error": "Failed to create post"}), 500

@post_bp.route("/<int:id>", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_post(id):
    """Update a post"""
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        # Check permissions
        if post.user_id != user.id and not user.is_admin:
            return jsonify({"error": "Unauthorized to edit this post"}), 403

        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Update fields
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            if len(title) > 200:
                return jsonify({"error": "Title must be under 200 characters"}), 400
            
            # Check for duplicate title
            duplicate = Post.query.filter(
                Post.title == title,
                Post.user_id == post.user_id,
                Post.id != post.id
            ).first()
            if duplicate:
                return jsonify({"error": "You already have a post with this title"}), 409
            
            post.title = title

        if "content" in data:
            content = data["content"].strip()
            if not content:
                return jsonify({"error": "Content cannot be empty"}), 400
            post.content = content

        if "tags" in data:
            post.tags = data["tags"].strip() or None

        post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post updated successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating post: {e}")
        return jsonify({"error": "Failed to update post"}), 500

@post_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_post(id):
    """Delete a post"""
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        # Check permissions
        if post.user_id != user.id and not user.is_admin:
            return jsonify({"error": "Unauthorized to delete this post"}), 403

        db.session.delete(post)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting post: {e}")
        return jsonify({"error": "Failed to delete post"}), 500

@post_bp.route("/<int:id>/like", methods=["POST"])
@jwt_required()
@block_check_required
def like_post(id):
    """Like or unlike a post"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get_or_404(id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Toggle like status
        if user in post.liked_by:
            post.liked_by.remove(user)
            message = "Post unliked successfully"
            liked = False
        else:
            post.liked_by.append(user)
            message = "Post liked successfully"
            liked = True

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "liked": liked,
            "likes_count": post.likes_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling post like: {e}")
        return jsonify({"error": "Failed to toggle like"}), 500

@post_bp.route("/<int:id>/approve", methods=["PATCH"])
@jwt_required()
def approve_post(id):
    """Approve or disapprove a post (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        post = Post.query.get_or_404(id)
        
        data = request.get_json()
        if data and "is_approved" in data:
            post.is_approved = bool(data["is_approved"])
        else:
            post.is_approved = not post.is_approved

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Post {'approved' if post.is_approved else 'disapproved'} successfully",
            "is_approved": post.is_approved
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving post: {e}")
        return jsonify({"error": "Failed to update post approval status"}), 500

@post_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
def flag_post(id):
    """Flag or unflag a post"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user:
            return jsonify({"error": "User not found"}), 404

        post = Post.query.get_or_404(id)
        
        data = request.get_json()
        if data and "is_flagged" in data:
            post.is_flagged = bool(data["is_flagged"])
        else:
            post.is_flagged = not post.is_flagged
            
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Post {'flagged' if post.is_flagged else 'unflagged'} successfully",
            "is_flagged": post.is_flagged
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error flagging post: {e}")
        return jsonify({"error": "Failed to update post flag status"}), 500

@post_bp.route("/flagged", methods=["GET"])
@jwt_required()
def get_flagged_posts():
    """Get all flagged posts (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        flagged_posts = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
        
        posts_data = []
        for post in flagged_posts:
            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "user_id": post.user_id,
                "username": post.author.username if post.author else "Unknown User",
                "is_flagged": post.is_flagged,
                "is_approved": post.is_approved,
                "likes_count": post.likes_count,
                "vote_score": post.vote_score,
                "created_at": post.created_at.isoformat(),
                "flagged_at": post.updated_at.isoformat() if post.updated_at else post.created_at.isoformat()
            }
            posts_data.append(post_data)

        return jsonify(posts_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching flagged posts: {e}")
        return jsonify({"error": "Failed to fetch flagged posts"}), 500

@post_bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_posts():
    """Get all pending approval posts (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        pending_posts = Post.query.filter_by(is_approved=False).order_by(Post.created_at.desc()).all()
        
        posts_data = []
        for post in pending_posts:
            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "user_id": post.user_id,
                "username": post.author.username if post.author else "Unknown User",
                "is_flagged": post.is_flagged,
                "is_approved": post.is_approved,
                "likes_count": post.likes_count,
                "vote_score": post.vote_score,
                "created_at": post.created_at.isoformat()
            }
            posts_data.append(post_data)

        return jsonify(posts_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching pending posts: {e}")
        return jsonify({"error": "Failed to fetch pending posts"}), 500