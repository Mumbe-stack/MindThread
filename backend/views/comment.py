from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post
from datetime import datetime, timezone
from .utils import block_check_required 
import traceback

comment_bp = Blueprint('comment_bp', __name__)


@comment_bp.route("", methods=["GET"])
def list_comments_no_slash():
    """Get comments for a specific post or user"""
    try:
        post_id = request.args.get("post_id")
        user_id = request.args.get("user_id")

        if not post_id and not user_id:
            return jsonify({"error": "post_id or user_id parameter is required"}), 400

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

        # Get comments ordered by creation date
        comments = query.order_by(Comment.created_at.asc()).all()

        # Get current user (optional authentication)
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except:
            pass  

        # Format comments data
        comments_data = []
        for c in comments:
            # Handle likes safely
            likes_count = 0
            liked_by_list = []
            
            try:
                if hasattr(c, 'liked_by_users') and c.liked_by_users:
                    likes_count = len(c.liked_by_users)
                    liked_by_list = [user.id for user in c.liked_by_users]
                elif hasattr(c, 'liked_by') and c.liked_by:
                    likes_count = len(c.liked_by)
                    liked_by_list = [user.id for user in c.liked_by]
                elif hasattr(c, 'likes'):
                    likes_count = c.likes if isinstance(c.likes, int) else len(c.likes) if c.likes else 0
            except Exception as like_error:
                print(f"Error processing likes for comment {c.id}: {like_error}")
                likes_count = 0
                liked_by_list = []

            comment_data = {
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "parent_id": getattr(c, 'parent_id', None),
                "created_at": c.created_at.isoformat() if c.created_at else datetime.now(timezone.utc).isoformat(),
                "likes": likes_count,
                "liked_by": liked_by_list,
                "is_approved": getattr(c, 'is_approved', True),
                "is_flagged": getattr(c, 'is_flagged', False)
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        print(f"Error fetching comments: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500


@comment_bp.route("/", methods=["GET"])
def list_comments():
    """Alternative endpoint with trailing slash"""
    return list_comments_no_slash()


@comment_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required
def create_comment():
    """Create a new comment"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()

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

        # Create comment
        comment = Comment(
            content=content,
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc)
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment created successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "parent_id": comment.parent_id,
                "created_at": comment.created_at.isoformat(),
                "likes": 0,
                "liked_by": []
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating comment: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create comment"}), 500


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

        # Initialize liked_by_users if it doesn't exist
        if not hasattr(comment, 'liked_by_users') or comment.liked_by_users is None:
            comment.liked_by_users = []

        # Toggle like status
        if user in comment.liked_by_users:
            comment.liked_by_users.remove(user)
            message = "Comment unliked"
        else:
            comment.liked_by_users.append(user)
            message = "Comment liked"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "likes": len(comment.liked_by_users),
            "liked_by": [u.id for u in comment.liked_by_users]
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error toggling comment like: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to toggle like"}), 500


@comment_bp.route("/<int:comment_id>/like/", methods=["POST", "OPTIONS"])
def like_comment_with_slash(comment_id):
    """Handle like requests with trailing slash"""
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    
    # Redirect to main like function
    return like_comment(comment_id)


@comment_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
@block_check_required
def update_comment(id):
    """Update a comment (only by owner)"""
    try:
        user_id = get_jwt_identity()
        comment = Comment.query.get(id)

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        if comment.user_id != user_id:
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
        comment.updated_at = datetime.now(timezone.utc)  # Add if you have this field
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment updated successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "updated_at": comment.updated_at.isoformat() if hasattr(comment, 'updated_at') else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating comment: {e}")
        print(f"Traceback: {traceback.format_exc()}")
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

        # Check if user owns the comment or is admin
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
        print(f"Error deleting comment: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete comment"}), 500


@comment_bp.route("/<int:parent_id>/replies", methods=["GET"])
def get_replies(parent_id):
    """Get replies to a specific comment"""
    try:
        parent = Comment.query.get(parent_id)
        if not parent:
            return jsonify({"error": f"Comment with ID {parent_id} does not exist"}), 404

        replies = Comment.query.filter_by(parent_id=parent_id).order_by(Comment.created_at.asc()).all()
        
        replies_data = []
        for reply in replies:
            # Handle likes safely
            likes_count = 0
            liked_by_list = []
            
            try:
                if hasattr(reply, 'liked_by_users') and reply.liked_by_users:
                    likes_count = len(reply.liked_by_users)
                    liked_by_list = [user.id for user in reply.liked_by_users]
            except Exception as like_error:
                print(f"Error processing likes for reply {reply.id}: {like_error}")

            replies_data.append({
                "id": reply.id,
                "content": reply.content,
                "post_id": reply.post_id,
                "user_id": reply.user_id,
                "parent_id": reply.parent_id,
                "created_at": reply.created_at.isoformat(),
                "likes": likes_count,
                "liked_by": liked_by_list
            })

        return jsonify(replies_data), 200

    except Exception as e:
        print(f"Error fetching replies: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch replies"}), 500


# Admin endpoints
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
            likes_count = 0
            try:
                if hasattr(c, 'liked_by_users') and c.liked_by_users:
                    likes_count = len(c.liked_by_users)
            except:
                pass

            comments_data.append({
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "created_at": c.created_at.isoformat(),
                "is_approved": getattr(c, 'is_approved', True),
                "is_flagged": getattr(c, 'is_flagged', False),
                "likes": likes_count
            })
            
        return jsonify(comments_data), 200
        
    except Exception as e:
        print(f"Error fetching all comments: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500


@comment_bp.route("/<int:id>/force", methods=["DELETE"])
@jwt_required()
@block_check_required
def force_delete_comment(id):
    """Force delete comment (admin only)"""
    try:
        admin = User.query.get(get_jwt_identity())
        if not admin or not admin.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        db.session.delete(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Comment ID {id} forcibly deleted by admin"
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error force deleting comment: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete comment"}), 500


@comment_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
@block_check_required
def flag_comment(id):
    """Flag comment for review (admin only)"""
    try:
        admin = User.query.get(get_jwt_identity())
        if not admin or not admin.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        comment.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Comment ID {id} flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error flagging comment: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to flag comment"}), 500


@comment_bp.route("/<int:id>/approve", methods=["PATCH"])
@jwt_required()
@block_check_required
def set_comment_approval(id):
    """Approve or reject comment (admin only)"""
    try:
        admin = User.query.get(get_jwt_identity())
        if not admin or not admin.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json()
        if not data or "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        comment.is_approved = bool(data["is_approved"])
        db.session.commit()

        status = "approved" if comment.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Comment ID {id} {status}"
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error setting comment approval: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update comment approval"}), 500


# Test endpoint
@comment_bp.route("/test", methods=["GET"])
def test_comments():
    """Test endpoint to verify comments system is working"""
    try:
        comment_count = Comment.query.count()
        return jsonify({
            "success": True,
            "message": "Comments system is working",
            "total_comments": comment_count,
            "endpoints": {
                "get_comments": "GET /api/comments?post_id=X",
                "create_comment": "POST /api/comments",
                "like_comment": "POST /api/comments/<id>/like",
                "update_comment": "PUT /api/comments/<id>",
                "delete_comment": "DELETE /api/comments/<id>",
                "get_replies": "GET /api/comments/<id>/replies"
            }
        }), 200
        
    except Exception as e:
        print(f"Error in test endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500


# Utility function for comment serialization
def comment_to_dict(comment):
    """Convert comment object to dictionary"""
    try:
        likes_count = 0
        liked_by_list = []
        
        if hasattr(comment, 'liked_by_users') and comment.liked_by_users:
            likes_count = len(comment.liked_by_users)
            liked_by_list = [user.id for user in comment.liked_by_users]
        
        return {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "user_id": comment.user_id,
            "post_id": comment.post_id,
            "parent_id": getattr(comment, 'parent_id', None),
            "is_flagged": getattr(comment, 'is_flagged', False),
            "is_approved": getattr(comment, 'is_approved', True),
            "likes": likes_count,
            "liked_by": liked_by_list
        }
    except Exception as e:
        print(f"Error converting comment to dict: {e}")
        return {
            "id": comment.id,
            "content": comment.content,
            "error": "Failed to load complete comment data"
        }