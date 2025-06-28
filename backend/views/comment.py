from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post, Vote, Like
from datetime import datetime, timezone
import traceback
import logging

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

logger = logging.getLogger(__name__)

comment_bp = Blueprint('comments', __name__)

def serialize_comment_with_stats(comment, current_user_id=None):
    """Serialize comment with all stats and user information"""
    try:
        # Get vote statistics
        upvotes = Vote.query.filter_by(comment_id=comment.id, value=1).count()
        downvotes = Vote.query.filter_by(comment_id=comment.id, value=-1).count()
        vote_score = upvotes - downvotes
        
        user_vote = None
        if current_user_id:
            uv = Vote.query.filter_by(comment_id=comment.id, user_id=current_user_id).first()
            user_vote = uv.value if uv else None
        
        likes_count = Like.query.filter_by(comment_id=comment.id).count()
        liked_by_user = False
        if current_user_id:
            liked_by_user = (
                Like.query.filter_by(comment_id=comment.id, user_id=current_user_id).first()
                is not None
            )
        
        author = User.query.get(comment.user_id)
        
        return {
            'id': comment.id,
            'content': comment.content,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'parent_id': comment.parent_id,
            'author': {
                'id': author.id,
                'username': author.username,
                'avatar_url': getattr(author, 'avatar_url', None)
            } if author else {"id": None, "username": "Unknown"},
            'username': author.username if author else "Unknown",
            'created_at': comment.created_at.isoformat() if comment.created_at else None,
            'updated_at': comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else None,
            'is_approved': getattr(comment, 'is_approved', True),
            'is_flagged': getattr(comment, 'is_flagged', False),
            'vote_score': vote_score,
            'upvotes': upvotes,
            'downvotes': downvotes,
            'total_votes': upvotes + downvotes,
            'userVote': user_vote,
            'likes_count': likes_count,
            'liked_by_user': liked_by_user,
            'replies_count': Comment.query.filter_by(parent_id=comment.id, is_approved=True).count() if hasattr(Comment, 'is_approved') else Comment.query.filter_by(parent_id=comment.id).count()
        }
    except Exception as e:
        logger.error(f"Error serializing comment {comment.id}: {e}")
        # Fallback serialization
        author = User.query.get(comment.user_id)
        return {
            'id': comment.id,
            'content': comment.content,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'parent_id': comment.parent_id,
            'author': {
                'id': author.id,
                'username': author.username
            } if author else {"id": None, "username": "Unknown"},
            'username': author.username if author else "Unknown",
            'created_at': comment.created_at.isoformat() if comment.created_at else None,
            'is_approved': getattr(comment, 'is_approved', True),
            'is_flagged': getattr(comment, 'is_flagged', False),
            'vote_score': 0,
            'likes_count': 0,
            'liked_by_user': False
        }

@comment_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
def get_post_comments(post_id):
    """Get comments for a specific post"""
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

        # Verify post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Build query for comments
        query = Comment.query.filter_by(post_id=post_id)
        
        # Filter by approval status unless user is admin or author
        if not (current_user and current_user.is_admin):
            query = query.filter(Comment.is_approved == True)
        
        # Get comments ordered by creation date
        comments = query.order_by(Comment.created_at.asc()).all()
        
        # Serialize comments
        comments_data = [serialize_comment_with_stats(c, current_user_id) for c in comments]
        
        return jsonify(comments_data), 200

    except Exception as e:
        logger.error(f"Error fetching comments for post {post_id}: {e}")
        return jsonify({"error": "Failed to fetch comments", "message": str(e)}), 500

@comment_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@jwt_required()
@block_check_required
def create_post_comment(post_id):
    """Create a new comment on a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        # Verify post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        content = data.get("content", "").strip()
        parent_id = data.get("parent_id")

        if not content:
            return jsonify({"error": "Comment content is required"}), 400

        if len(content) > 1000:
            return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400

        # Validate parent comment if provided
        if parent_id:
            try:
                parent_id = int(parent_id)
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment or parent_comment.post_id != post_id:
                    return jsonify({"error": "Invalid parent comment"}), 400
            except ValueError:
                return jsonify({"error": "Invalid parent_id format"}), 400

        # Comments require approval by default (except for admins)
        is_approved = current_user.is_admin

        # Create comment
        comment = Comment(
            content=content,
            post_id=post_id,
            user_id=current_user_id,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc),
            is_approved=is_approved,
            is_flagged=False
        )

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)

        db.session.add(comment)
        db.session.commit()

        # Serialize the new comment
        comment_data = serialize_comment_with_stats(comment, current_user_id)
        
        if not is_approved:
            comment_data['message'] = 'Comment posted successfully and is pending admin approval'
        else:
            comment_data['message'] = 'Comment posted and approved automatically'

        return jsonify(comment_data), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating comment: {e}")
        return jsonify({"error": "Failed to create comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["GET"])
def get_comment(comment_id):
    """Get a specific comment"""
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

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check if user can view this comment
        can_view = (
            getattr(comment, 'is_approved', True) or  # Comment is approved
            (current_user and current_user.is_admin) or  # User is admin
            (current_user_id == comment.user_id)  # User is the author
        )

        if not can_view:
            return jsonify({"error": "Comment not found"}), 404

        comment_data = serialize_comment_with_stats(comment, current_user_id)
        return jsonify(comment_data), 200

    except Exception as e:
        logger.error(f"Error fetching comment {comment_id}: {e}")
        return jsonify({"error": "Failed to fetch comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_comment(comment_id):
    """Update a specific comment"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        comment = Comment.query.get(comment_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        if comment.user_id != current_user_id and not current_user.is_admin:
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        # Regular users editing their comment requires re-approval
        requires_reapproval = False

        if 'content' in data:
            content = data['content'].strip()
            if not content: 
                return jsonify({"error": "Content cannot be empty"}), 400
            if len(content) > 1000:
                return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400
            if comment.content != content:
                comment.content = content
                requires_reapproval = True

        # Admin-only fields
        if current_user.is_admin:
            if 'is_approved' in data: 
                comment.is_approved = bool(data['is_approved'])
                requires_reapproval = False  # Admin is handling approval
            if 'is_flagged' in data: 
                comment.is_flagged = bool(data['is_flagged'])
        else:
            # Non-admin users need re-approval if they edit content
            if requires_reapproval and getattr(comment, 'is_approved', True):
                comment.is_approved = False

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        comment_data = serialize_comment_with_stats(comment, current_user_id)
        if requires_reapproval and not current_user.is_admin:
            comment_data['message'] = 'Comment updated successfully and is pending admin approval'

        return jsonify(comment_data), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating comment {comment_id}: {e}")
        return jsonify({"error": "Failed to update comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_comment(comment_id):
    """Delete a specific comment"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        comment = Comment.query.get(comment_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        if comment.user_id != current_user_id and not current_user.is_admin:
            return jsonify({"error": "Permission denied"}), 403

        # Delete related data first
        Like.query.filter_by(comment_id=comment_id).delete()
        Vote.query.filter_by(comment_id=comment_id).delete()
        
        # Delete replies
        Comment.query.filter_by(parent_id=comment_id).delete()
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({"message": "Comment deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment {comment_id}: {e}")
        return jsonify({"error": "Failed to delete comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>/like", methods=["POST"])
@jwt_required()
@block_check_required
def toggle_comment_like(comment_id):
    """Toggle like on a comment"""
    try:
        current_user_id = get_jwt_identity()
        comment = Comment.query.get(comment_id)
        
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        existing = Like.query.filter_by(comment_id=comment_id, user_id=current_user_id).first()
        if existing:
            db.session.delete(existing)
            message = "Comment unliked"
            liked = False
        else:
            new_like = Like(
                comment_id=comment_id,
                user_id=current_user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_like)
            message = "Comment liked"
            liked = True

        db.session.commit()
        
        likes_count = Like.query.filter_by(comment_id=comment_id).count()
        return jsonify({
            "message": message,
            "likes": likes_count,
            "likes_count": likes_count,
            "liked_by_user": liked
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on comment {comment_id}: {e}")
        return jsonify({"error": "Failed to toggle like", "message": str(e)}), 500

# General comments endpoint for admin use
@comment_bp.route("/comments", methods=["GET"])
def list_comments():
    """Get comments with various filters (mainly for admin use)"""
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

        # Get query parameters
        post_id = request.args.get("post_id", type=int)
        user_id = request.args.get("user_id", type=int)
        all_comments = request.args.get("all", "").lower() == "true"
        admin_mode = request.args.get("admin", "").lower() == "true"
        limit = min(request.args.get("limit", 100, type=int), 500)

        # Build query
        query = Comment.query

        # Apply filters
        if post_id:
            query = query.filter_by(post_id=post_id)
        if user_id:
            query = query.filter_by(user_id=user_id)

        # Filter by approval status unless admin
        if not (current_user and current_user.is_admin and (all_comments or admin_mode)):
            if hasattr(Comment, 'is_approved'):
                query = query.filter(Comment.is_approved == True)

        # Order and limit
        comments = query.order_by(Comment.created_at.desc()).limit(limit).all()
        
        # Serialize comments
        comments_data = [serialize_comment_with_stats(c, current_user_id) for c in comments]
        
        return jsonify(comments_data), 200

    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return jsonify({"error": "Failed to fetch comments", "message": str(e)}), 500

# ADMIN ROUTES
@comment_bp.route("/admin/comments/<int:comment_id>/approve", methods=["PATCH"])
@jwt_required()
def admin_approve_comment(comment_id):
    """Admin: Approve or reject a comment"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json() or {}
        is_approved = bool(data.get('is_approved', True))
        
        comment.is_approved = is_approved
        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        action = 'approved' if is_approved else 'rejected'
        return jsonify({
            "message": f"Comment {action} successfully",
            "comment": serialize_comment_with_stats(comment, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving comment {comment_id}: {e}")
        return jsonify({"error": "Failed to update approval", "message": str(e)}), 500

@comment_bp.route("/admin/comments/<int:comment_id>/flag", methods=["PATCH"])
@jwt_required()
def admin_flag_comment(comment_id):
    """Admin: Flag or unflag a comment"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json() or {}
        is_flagged = bool(data.get('is_flagged', True))

        comment.is_flagged = is_flagged
        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = 'flagged' if is_flagged else 'unflagged'
        return jsonify({
            "message": f"Comment {action} successfully",
            "comment": serialize_comment_with_stats(comment, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging comment {comment_id}: {e}")
        return jsonify({"error": "Failed to flag comment", "message": str(e)}), 500

# Test endpoint
@comment_bp.route("/comments/test", methods=["GET"])
def test_comments():
    """Test endpoint to verify comments system is working"""
    try:
        comment_count = Comment.query.count()
        
        # Safe attribute checking
        approved_count = 0
        flagged_count = 0
        
        if hasattr(Comment, 'is_approved'):
            approved_count = Comment.query.filter_by(is_approved=True).count()
        if hasattr(Comment, 'is_flagged'):
            flagged_count = Comment.query.filter_by(is_flagged=True).count()
        
        return jsonify({
            "success": True,
            "message": "Comments system is working",
            "total_comments": comment_count,
            "approved_comments": approved_count,
            "flagged_comments": flagged_count,
            "features": {
                "approval_system": hasattr(Comment, 'is_approved'),
                "flagging_system": hasattr(Comment, 'is_flagged'),
                "voting_system": True,
                "like_system": True
            },
            "endpoints": {
                "get_post_comments": "GET /api/posts/<id>/comments",
                "create_comment": "POST /api/posts/<id>/comments",
                "get_comment": "GET /api/comments/<id>",
                "update_comment": "PATCH /api/comments/<id>",
                "delete_comment": "DELETE /api/comments/<id>",
                "like_comment": "POST /api/comments/<id>/like",
                "admin_approve": "PATCH /api/admin/comments/<id>/approve",
                "admin_flag": "PATCH /api/admin/comments/<id>/flag"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500