from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post, Vote, Like
from datetime import datetime, timezone
import traceback

# Import utils if available, otherwise define a simple decorator
try:
    from .utils import block_check_required
except ImportError:
    def block_check_required(f):
        """Simple decorator if utils not available"""
        def wrapper(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                if current_user and current_user.is_blocked:
                    return jsonify({"error": "User is blocked"}), 403
                return f(*args, **kwargs)
            except Exception as e:
                return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper

# FIXED: Remove url_prefix since app.py handles it
comment_bp = Blueprint('comments', __name__)

@comment_bp.route("/comments", methods=["GET"])
def list_comments():
    """Get comments for a specific post or user - only approved comments for non-admins"""
    try:
        post_id = request.args.get("post_id")
        user_id = request.args.get("user_id")

        if not post_id and not user_id:
            return jsonify({"error": "post_id or user_id parameter is required"}), 400

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

        # Build query
        query = Comment.query
        if post_id:
            try:
                post_id = int(post_id)
                query = query.filter_by(post_id=post_id)
            except ValueError:
                return jsonify({"error": "Invalid post_id format"}), 400
                
        if user_id:
            try:
                user_id = int(user_id)
                query = query.filter_by(user_id=user_id)
            except ValueError:
                return jsonify({"error": "Invalid user_id format"}), 400

        # Filter by approval status (non-admins see only approved)
        if not (current_user and current_user.is_admin):
            query = query.filter_by(is_approved=True)

        # Get comments ordered by creation date
        comments = query.order_by(Comment.created_at.asc()).all()

        # Format comments data
        comments_data = []
        for c in comments:
            # Get user's vote on this comment if logged in
            user_vote = None
            if current_user_id:
                vote = Vote.query.filter_by(user_id=current_user_id, comment_id=c.id).first()
                user_vote = vote.value if vote else None

            # Get user's like status
            user_liked = False
            if current_user_id:
                like = Like.query.filter_by(user_id=current_user_id, comment_id=c.id).first()
                user_liked = like is not None

            comment_data = {
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "author": {
                    "id": c.user_id,
                    "username": c.user.username if c.user else "Unknown User"
                },
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat() if c.created_at else datetime.now(timezone.utc).isoformat(),
                "updated_at": c.updated_at.isoformat() if hasattr(c, 'updated_at') and c.updated_at else None,
                "likes_count": c.likes_count,
                "vote_score": c.vote_score,
                "upvotes_count": c.upvotes_count,
                "downvotes_count": c.downvotes_count,
                "total_votes": c.total_votes,
                "is_approved": c.is_approved,
                "is_flagged": c.is_flagged,
                "user_vote": user_vote,
                "user_liked": user_liked
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching comments: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500

@comment_bp.route("/comments", methods=["POST"])
@jwt_required()
@block_check_required
def create_comment():
    """Create a new comment"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        # Validate required fields
        if not data or not data.get("content") or not data.get("post_id"):
            return jsonify({"error": "Missing fields: content and post_id are required"}), 400

        # Validate content
        content = data["content"].strip()
        if len(content) < 1:
            return jsonify({"error": "Comment content cannot be empty"}), 400

        if len(content) > 1000:
            return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400

        # Validate post exists
        try:
            post_id = int(data["post_id"])
            post = Post.query.get(post_id)
            if not post:
                return jsonify({"error": f"Post with ID {post_id} does not exist"}), 404
        except ValueError:
            return jsonify({"error": "Invalid post_id format"}), 400

        # Validate parent comment if provided
        parent_id = data.get("parent_id")
        if parent_id:
            try:
                parent_id = int(parent_id)
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment:
                    return jsonify({"error": f"Parent comment with ID {parent_id} does not exist"}), 404
            except ValueError:
                return jsonify({"error": "Invalid parent_id format"}), 400

        # Create comment - auto-approve for admins
        comment = Comment(
            content=content,
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc),
            is_approved=user.is_admin,  # Auto-approve admin comments
            is_flagged=False
        )

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)

        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment created successfully" + (" and approved" if user.is_admin else " - pending approval"),
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "author": {
                    "id": user.id,
                    "username": user.username
                },
                "parent_id": comment.parent_id,
                "created_at": comment.created_at.isoformat(),
                "is_approved": comment.is_approved,
                "is_flagged": comment.is_flagged,
                "likes_count": 0,
                "vote_score": 0,
                "upvotes_count": 0,
                "downvotes_count": 0,
                "total_votes": 0
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create comment"}), 500

@comment_bp.route("/comments/<int:comment_id>/like", methods=["POST"])
@jwt_required()
@block_check_required
def like_comment(comment_id):
    """Like or unlike a comment"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        comment = Comment.query.get(comment_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check if user already liked this comment
        existing_like = Like.query.filter_by(
            user_id=user_id,
            comment_id=comment_id
        ).first()

        if existing_like:
            # Unlike the comment
            db.session.delete(existing_like)
            message = "Comment unliked"
            liked = False
        else:
            # Like the comment
            new_like = Like(
                user_id=user_id,
                comment_id=comment_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_like)
            message = "Comment liked"
            liked = True

        db.session.commit()

        # Get updated like count
        likes_count = Like.query.filter_by(comment_id=comment_id).count()

        return jsonify({
            "success": True,
            "message": message,
            "liked": liked,
            "likes_count": likes_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling comment like: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to toggle like"}), 500

@comment_bp.route("/comments/<int:id>", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_comment(id):
    """Update a comment (only by owner or admin)"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        comment = Comment.query.get(id)

        if not current_user:
            return jsonify({"error": "User not found"}), 404

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check permissions
        if comment.user_id != user_id and not current_user.is_admin:
            return jsonify({"error": "You can only edit your own comment"}), 403

        data = request.get_json()
        if not data or not data.get("content"):
            return jsonify({"error": "Content is required"}), 400

        content = data["content"].strip()
        if len(content) < 1:
            return jsonify({"error": "Comment content cannot be empty"}), 400

        if len(content) > 1000:
            return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400

        comment.content = content
        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment updated successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "updated_at": comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update comment"}), 500

@comment_bp.route("/comments/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_comment(id):
    """Delete a comment (only by owner or admin)"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        comment = Comment.query.get(id)

        if not current_user:
            return jsonify({"error": "User not found"}), 404

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check permissions
        if comment.user_id != user_id and not current_user.is_admin:
            return jsonify({"error": "You can only delete your own comment"}), 403

        # Store comment info for response
        comment_info = {
            "id": comment.id,
            "content": comment.content,
            "deleted_by": "owner" if comment.user_id == user_id else "admin"
        }

        # Delete related likes and votes first
        Like.query.filter_by(comment_id=id).delete()
        Vote.query.filter_by(comment_id=id).delete()

        # Delete the comment
        db.session.delete(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Comment ID {id} deleted successfully",
            "comment": comment_info
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete comment"}), 500

@comment_bp.route("/comments/<int:id>/approve", methods=["PATCH"])
@jwt_required()
def approve_comment(id):
    """Approve or disapprove a comment (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get_or_404(id)
        
        data = request.get_json()
        if data and "is_approved" in data:
            comment.is_approved = bool(data["is_approved"])
        else:
            comment.is_approved = not comment.is_approved

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Comment {'approved' if comment.is_approved else 'disapproved'} successfully",
            "is_approved": comment.is_approved
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update comment approval status"}), 500

@comment_bp.route("/comments/<int:id>/flag", methods=["PATCH"])
@jwt_required()
def flag_comment(id):
    """Flag or unflag a comment"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user:
            return jsonify({"error": "User not found"}), 404

        comment = Comment.query.get_or_404(id)
        
        data = request.get_json()
        if data and "is_flagged" in data:
            comment.is_flagged = bool(data["is_flagged"])
        else:
            comment.is_flagged = not comment.is_flagged

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Comment {'flagged' if comment.is_flagged else 'unflagged'} successfully",
            "is_flagged": comment.is_flagged
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error flagging comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update comment flag status"}), 500

# Test endpoint
@comment_bp.route("/comments/test", methods=["GET"])
def test_comments():
    """Test endpoint to verify comments system is working"""
    try:
        comment_count = Comment.query.count()
        approved_count = Comment.query.filter_by(is_approved=True).count()
        flagged_count = Comment.query.filter_by(is_flagged=True).count()
        
        return jsonify({
            "success": True,
            "message": "Comments system is working",
            "total_comments": comment_count,
            "approved_comments": approved_count,
            "flagged_comments": flagged_count,
            "endpoints": {
                "get_comments": "GET /api/comments?post_id=X",
                "create_comment": "POST /api/comments",
                "like_comment": "POST /api/comments/<id>/like",
                "update_comment": "PATCH /api/comments/<id>",
                "delete_comment": "DELETE /api/comments/<id>",
                "approve_comment": "PATCH /api/comments/<id>/approve",
                "flag_comment": "PATCH /api/comments/<id>/flag"
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in test endpoint: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500