from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post, Vote
from datetime import datetime, timezone
from .utils import block_check_required 
import traceback

comment_bp = Blueprint('comment_bp', __name__)

@comment_bp.route("", methods=["GET"])
def list_comments_no_slash():
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

            comment_data = {
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "username": c.author.username if c.author else "Unknown User",
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat() if c.created_at else datetime.now(timezone.utc).isoformat(),
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "likes_count": c.likes_count,
                "vote_score": c.vote_score,
                "upvotes_count": c.upvotes_count,
                "downvotes_count": c.downvotes_count,
                "is_approved": c.is_approved,
                "is_flagged": c.is_flagged,
                "user_vote": user_vote
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching comments: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500

@comment_bp.route("/", methods=["GET"])
def list_comments():
    """Alternative endpoint with trailing slash"""
    return list_comments_no_slash()

@comment_bp.route("", methods=["POST"])
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
                "username": user.username,
                "parent_id": comment.parent_id,
                "created_at": comment.created_at.isoformat(),
                "is_approved": comment.is_approved,
                "is_flagged": comment.is_flagged,
                "likes_count": 0,
                "vote_score": 0,
                "upvotes_count": 0,
                "downvotes_count": 0
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create comment"}), 500

@comment_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required
def create_comment_with_slash():
    """Create comment endpoint with trailing slash"""
    return create_comment()

@comment_bp.route("/<int:comment_id>/like", methods=["POST"])
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

        # Toggle like status
        if user in comment.liked_by_users:
            comment.liked_by_users.remove(user)
            message = "Comment unliked"
            liked = False
        else:
            comment.liked_by_users.append(user)
            message = "Comment liked"
            liked = True

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "liked": liked,
            "likes_count": comment.likes_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling comment like: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to toggle like"}), 500

@comment_bp.route("/<int:id>", methods=["PATCH"])
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
        comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment updated successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "updated_at": comment.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating comment: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update comment"}), 500

@comment_bp.route("/<int:id>", methods=["DELETE"])
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

@comment_bp.route("/<int:id>/approve", methods=["PATCH"])
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

@comment_bp.route("/<int:id>/flag", methods=["PATCH"])
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

@comment_bp.route("/flagged", methods=["GET"])
@jwt_required()
def get_flagged_comments():
    """Get all flagged comments (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        flagged_comments = Comment.query.filter_by(is_flagged=True).order_by(Comment.created_at.desc()).all()
        
        comments_data = []
        for comment in flagged_comments:
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "username": comment.author.username if comment.author else "Unknown User",
                "is_flagged": comment.is_flagged,
                "is_approved": comment.is_approved,
                "likes_count": comment.likes_count,
                "vote_score": comment.vote_score,
                "created_at": comment.created_at.isoformat(),
                "flagged_at": comment.updated_at.isoformat() if comment.updated_at else comment.created_at.isoformat()
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching flagged comments: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch flagged comments"}), 500

@comment_bp.route("/pending", methods=["GET"])
@jwt_required()
def get_pending_comments():
    """Get all pending approval comments (admin only)"""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        pending_comments = Comment.query.filter_by(is_approved=False).order_by(Comment.created_at.desc()).all()
        
        comments_data = []
        for comment in pending_comments:
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "username": comment.author.username if comment.author else "Unknown User",
                "is_flagged": comment.is_flagged,
                "is_approved": comment.is_approved,
                "likes_count": comment.likes_count,
                "vote_score": comment.vote_score,
                "created_at": comment.created_at.isoformat()
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching pending comments: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch pending comments"}), 500

@comment_bp.route("/<int:parent_id>/replies", methods=["GET"])
def get_replies(parent_id):
    """Get replies to a specific comment - only approved for non-admins"""
    try:
        parent = Comment.query.get(parent_id)
        if not parent:
            return jsonify({"error": f"Comment with ID {parent_id} does not exist"}), 404

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

        # Filter replies by approval status
        replies_query = Comment.query.filter_by(parent_id=parent_id)
        if not (current_user and current_user.is_admin):
            replies_query = replies_query.filter_by(is_approved=True)
        
        replies = replies_query.order_by(Comment.created_at.asc()).all()
        
        replies_data = []
        for reply in replies:
            # Get user's vote on this reply if logged in
            user_vote = None
            if current_user_id:
                vote = Vote.query.filter_by(user_id=current_user_id, comment_id=reply.id).first()
                user_vote = vote.value if vote else None

            replies_data.append({
                "id": reply.id,
                "content": reply.content,
                "post_id": reply.post_id,
                "user_id": reply.user_id,
                "username": reply.author.username if reply.author else "Unknown User",
                "parent_id": reply.parent_id,
                "created_at": reply.created_at.isoformat(),
                "is_approved": reply.is_approved,
                "is_flagged": reply.is_flagged,
                "likes_count": reply.likes_count,
                "vote_score": reply.vote_score,
                "upvotes_count": reply.upvotes_count,
                "downvotes_count": reply.downvotes_count,
                "user_vote": user_vote
            })

        return jsonify(replies_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching replies: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch replies"}), 500

# Admin endpoint to get all comments
@comment_bp.route("/admin", methods=["GET"])
@jwt_required()
def get_all_comments():
    """Get all comments (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
            
        comments = Comment.query.order_by(Comment.created_at.desc()).all()
        
        comments_data = []
        for c in comments:
            comments_data.append({
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "username": c.author.username if c.author else "Unknown User",
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat(),
                "is_approved": c.is_approved,
                "is_flagged": c.is_flagged,
                "likes_count": c.likes_count,
                "vote_score": c.vote_score,
                "upvotes_count": c.upvotes_count,
                "downvotes_count": c.downvotes_count
            })
            
        return jsonify(comments_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching all comments: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500

# Test endpoint
@comment_bp.route("/test", methods=["GET"])
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
                "flag_comment": "PATCH /api/comments/<id>/flag",
                "get_replies": "GET /api/comments/<id>/replies"
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in test endpoint: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500