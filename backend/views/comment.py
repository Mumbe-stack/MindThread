from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, Post, User, Vote, Like
from datetime import datetime, timezone
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
comment_bp = Blueprint('comments', __name__)

def serialize_comment(comment, current_user_id=None):
    """Serialize comment object to dict"""
    author = User.query.get(comment.user_id)
    
    # Calculate vote metrics
    upvotes = Vote.query.filter_by(comment_id=comment.id, value=1).count()
    downvotes = Vote.query.filter_by(comment_id=comment.id, value=-1).count()
    vote_score = upvotes - downvotes
    
    # User's vote on this comment
    user_vote = None
    if current_user_id:
        user_vote_obj = Vote.query.filter_by(
            comment_id=comment.id, 
            user_id=current_user_id
        ).first()
        user_vote = user_vote_obj.value if user_vote_obj else None
    
    # Like status
    likes_count = Like.query.filter_by(comment_id=comment.id).count()
    liked_by_user = False
    if current_user_id:
        liked_by_user = Like.query.filter_by(
            comment_id=comment.id,
            user_id=current_user_id
        ).first() is not None
    
    return {
        'id': comment.id,
        'content': comment.content,
        'post_id': comment.post_id,
        'parent_id': comment.parent_id,
        'author': {
            'id': author.id,
            'username': author.username
        } if author else {"id": None, "username": "Unknown"},
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'vote_score': vote_score,
        'user_vote': user_vote,
        'likes_count': likes_count,
        'liked_by_user': liked_by_user,
        'replies_count': Comment.query.filter_by(parent_id=comment.id, is_approved=True).count()
    }

@comment_bp.route("/comments", methods=["GET"])
def get_comments():
    """Get comments for a post or all comments"""
    try:
        # Optional authentication
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except Exception:
            pass
        
        post_id = request.args.get('post_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        parent_id = request.args.get('parent_id', type=int)
        
        # Base query
        query = Comment.query
        
        # Filter by post
        if post_id:
            query = query.filter_by(post_id=post_id)
        
        # Filter by parent (for replies)
        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)
        else:
            query = query.filter_by(parent_id=None)  # Top-level comments only
        
        # Only show approved comments unless user is admin
        if not (current_user and current_user.is_admin):
            query = query.filter_by(is_approved=True)
        
        # Sorting
        if sort_by == 'updated_at':
            query = query.order_by(
                desc(Comment.updated_at) if order == 'desc' else Comment.updated_at
            )
        else:  # Default: created_at
            query = query.order_by(
                desc(Comment.created_at) if order == 'desc' else Comment.created_at
            )
        
        # Pagination
        comments = query.offset((page - 1) * per_page).limit(per_page).all()
        
        comments_data = []
        for comment in comments:
            comment_data = serialize_comment(comment, current_user_id)
            
            # Add replies if this is a top-level comment
            if not parent_id:
                replies = Comment.query.filter_by(
                    parent_id=comment.id,
                    is_approved=True
                ).order_by(Comment.created_at.asc()).limit(5).all()
                
                comment_data['replies'] = [
                    serialize_comment(reply, current_user_id) for reply in replies
                ]
                comment_data['has_more_replies'] = Comment.query.filter_by(
                    parent_id=comment.id,
                    is_approved=True
                ).count() > 5
            
            comments_data.append(comment_data)
        
        return jsonify({
            "comments": comments_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": query.count(),
                "post_id": post_id,
                "parent_id": parent_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return jsonify({'error': 'Failed to fetch comments'}), 500

@comment_bp.route("/comments", methods=["POST"])
@jwt_required()
def create_comment():
    """Create a new comment"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is blocked
        if user and getattr(user, 'is_blocked', False):
            return jsonify({"error": "User is blocked"}), 403
        
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('content', '').strip():
            return jsonify({"error": "Content is required"}), 400
        
        post_id = data.get('post_id')
        parent_id = data.get('parent_id')
        content = data.get('content', '').strip()
        
        if len(content) > 1000:
            return jsonify({"error": "Content must be under 1,000 characters"}), 400
        
        # Verify post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Verify parent comment exists if provided
        if parent_id:
            parent_comment = Comment.query.get(parent_id)
            if not parent_comment or parent_comment.post_id != post_id:
                return jsonify({"error": "Invalid parent comment"}), 400
        
        # Create comment
        comment = Comment(
            content=content,
            post_id=post_id,
            parent_id=parent_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_approved=True,  # Auto-approve for now
            is_flagged=False
        )
        
        db.session.add(comment)
        db.session.commit()
        
        response_data = serialize_comment(comment, user_id)
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating comment: {e}")
        return jsonify({'error': 'Failed to create comment'}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["GET"])
def get_comment(comment_id):
    """Get a single comment with replies"""
    try:
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except Exception:
            pass
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check if user can see this comment
        if not comment.is_approved and (
            not current_user or 
            (comment.user_id != current_user_id and not current_user.is_admin)
        ):
            return jsonify({'error': 'Comment not found'}), 404
        
        comment_data = serialize_comment(comment, current_user_id)
        
        # Add all replies
        replies = Comment.query.filter_by(
            parent_id=comment.id,
            is_approved=True
        ).order_by(Comment.created_at.asc()).all()
        
        comment_data['replies'] = [
            serialize_comment(reply, current_user_id) for reply in replies
        ]
        
        return jsonify(comment_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching comment: {e}")
        return jsonify({'error': 'Failed to fetch comment'}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["PATCH"])
@jwt_required()
def update_comment(comment_id):
    """Update a comment (author or admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is blocked
        if user and getattr(user, 'is_blocked', False):
            return jsonify({"error": "User is blocked"}), 403
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check permissions
        if comment.user_id != user_id and not user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update content
        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({'error': 'Content cannot be empty'}), 400
            if len(content) > 1000:
                return jsonify({'error': 'Content too long'}), 400
            
            comment.content = content
        
        # Admin can change approval status
        if user.is_admin:
            if 'is_approved' in data:
                comment.is_approved = bool(data['is_approved'])
            if 'is_flagged' in data:
                comment.is_flagged = bool(data['is_flagged'])
        
        comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify(serialize_comment(comment, user_id)), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating comment: {e}")
        return jsonify({'error': 'Failed to update comment'}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    """Delete a comment (author or admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check permissions
        if comment.user_id != user_id and not user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete comment and its replies
        Comment.query.filter_by(parent_id=comment_id).delete()
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({'message': 'Comment deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment: {e}")
        return jsonify({'error': 'Failed to delete comment'}), 500

@comment_bp.route("/comments/<int:comment_id>/like", methods=["POST"])
@jwt_required()
def toggle_comment_like(comment_id):
    """Like or unlike a comment"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is blocked
        if user and getattr(user, 'is_blocked', False):
            return jsonify({"error": "User is blocked"}), 403
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        existing_like = Like.query.filter_by(
            comment_id=comment_id,
            user_id=user_id
        ).first()
        
        if existing_like:
            db.session.delete(existing_like)
            action = 'unliked'
        else:
            like = Like(
                comment_id=comment_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(like)
            action = 'liked'
        
        db.session.commit()
        
        likes_count = Like.query.filter_by(comment_id=comment_id).count()
        
        return jsonify({
            'message': f'Comment {action}',
            'likes_count': likes_count,
            'liked_by_user': action == 'liked'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling comment like: {e}")
        return jsonify({'error': 'Failed to toggle like'}), 500

@comment_bp.route("/comments/<int:comment_id>/flag", methods=["PATCH"])
@jwt_required()
def flag_comment(comment_id):
    """Flag or unflag a comment"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        data = request.get_json() or {}
        flag = bool(data.get('is_flagged', True))
        
        # Only admin can unflag
        if not flag and not user.is_admin:
            return jsonify({'error': 'Only admin can unflag content'}), 403
        
        comment.is_flagged = flag
        comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        status = 'flagged' if comment.is_flagged else 'unflagged'
        
        return jsonify({
            'message': f'Comment {status}',
            'comment': serialize_comment(comment, user_id)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging comment: {e}")
        return jsonify({'error': 'Failed to flag comment'}), 500

@comment_bp.route("/comments/<int:comment_id>/approve", methods=["PATCH"])
@jwt_required()
def approve_comment(comment_id):
    """Approve or reject a comment (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        data = request.get_json() or {}
        comment.is_approved = bool(data.get('is_approved', True))
        comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        status = 'approved' if comment.is_approved else 'rejected'
        
        return jsonify({
            'message': f'Comment {status}',
            'comment': serialize_comment(comment, user_id)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving comment: {e}")
        return jsonify({'error': 'Failed to approve comment'}), 500