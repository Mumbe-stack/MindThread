from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Vote, Post, Comment, User
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
vote_bp = Blueprint('votes', __name__)

@vote_bp.route("/votes/post/<int:post_id>", methods=["POST"])
@jwt_required()
def vote_on_post(post_id):
    """Vote on a post (upvote/downvote/remove vote)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is blocked
        if user and getattr(user, 'is_blocked', False):
            return jsonify({"error": "User is blocked"}), 403
        
        data = request.get_json() or {}
        
        # Validate vote value
        vote_value = data.get('value')
        if vote_value not in [1, -1, 0]:
            return jsonify({"error": "Vote value must be 1 (upvote), -1 (downvote), or 0 (remove vote)"}), 400
        
        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Check if user already voted
        existing_vote = Vote.query.filter_by(
            post_id=post_id,
            user_id=user_id
        ).first()
        
        if vote_value == 0:
            # Remove vote
            if existing_vote:
                db.session.delete(existing_vote)
                action = "removed"
            else:
                action = "no change"
        else:
            # Add or update vote
            if existing_vote:
                if existing_vote.value == vote_value:
                    # Same vote - remove it (toggle behavior)
                    db.session.delete(existing_vote)
                    action = "removed"
                    vote_value = 0
                else:
                    # Different vote - update it
                    existing_vote.value = vote_value
                    existing_vote.updated_at = datetime.now(timezone.utc)
                    action = "updated"
            else:
                # New vote
                new_vote = Vote(
                    post_id=post_id,
                    user_id=user_id,
                    value=vote_value,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.session.add(new_vote)
                action = "added"
        
        db.session.commit()
        
        # Get updated vote counts
        upvotes = Vote.query.filter_by(post_id=post_id, value=1).count()
        downvotes = Vote.query.filter_by(post_id=post_id, value=-1).count()
        vote_score = upvotes - downvotes
        
        # Get user's current vote
        user_vote = Vote.query.filter_by(post_id=post_id, user_id=user_id).first()
        user_vote_value = user_vote.value if user_vote else None
        
        return jsonify({
            "success": True,
            "message": f"Vote {action}",
            "upvotes": upvotes,
            "downvotes": downvotes,
            "vote_score": vote_score,
            "total_votes": upvotes + downvotes,
            "user_vote": user_vote_value,
            "action": action
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error voting on post {post_id}: {e}")
        return jsonify({"error": "Failed to process vote"}), 500

@vote_bp.route("/votes/comment/<int:comment_id>", methods=["POST"])
@jwt_required()
def vote_on_comment(comment_id):
    """Vote on a comment (upvote/downvote/remove vote)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is blocked
        if user and getattr(user, 'is_blocked', False):
            return jsonify({"error": "User is blocked"}), 403
        
        data = request.get_json() or {}
        
        # Validate vote value
        vote_value = data.get('value')
        if vote_value not in [1, -1, 0]:
            return jsonify({"error": "Vote value must be 1 (upvote), -1 (downvote), or 0 (remove vote)"}), 400
        
        # Check if comment exists
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Check if user already voted
        existing_vote = Vote.query.filter_by(
            comment_id=comment_id,
            user_id=user_id
        ).first()
        
        if vote_value == 0:
            # Remove vote
            if existing_vote:
                db.session.delete(existing_vote)
                action = "removed"
            else:
                action = "no change"
        else:
            # Add or update vote
            if existing_vote:
                if existing_vote.value == vote_value:
                    # Same vote - remove it (toggle behavior)
                    db.session.delete(existing_vote)
                    action = "removed"
                    vote_value = 0
                else:
                    # Different vote - update it
                    existing_vote.value = vote_value
                    existing_vote.updated_at = datetime.now(timezone.utc)
                    action = "updated"
            else:
                # New vote
                new_vote = Vote(
                    comment_id=comment_id,
                    user_id=user_id,
                    value=vote_value,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.session.add(new_vote)
                action = "added"
        
        db.session.commit()
        
        # Get updated vote counts
        upvotes = Vote.query.filter_by(comment_id=comment_id, value=1).count()
        downvotes = Vote.query.filter_by(comment_id=comment_id, value=-1).count()
        vote_score = upvotes - downvotes
        
        # Get user's current vote
        user_vote = Vote.query.filter_by(comment_id=comment_id, user_id=user_id).first()
        user_vote_value = user_vote.value if user_vote else None
        
        return jsonify({
            "success": True,
            "message": f"Vote {action}",
            "upvotes": upvotes,
            "downvotes": downvotes,
            "vote_score": vote_score,
            "total_votes": upvotes + downvotes,
            "user_vote": user_vote_value,
            "action": action
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error voting on comment {comment_id}: {e}")
        return jsonify({"error": "Failed to process vote"}), 500

@vote_bp.route("/votes/post/<int:post_id>", methods=["GET"])
def get_post_votes(post_id):
    """Get vote information for a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        upvotes = Vote.query.filter_by(post_id=post_id, value=1).count()
        downvotes = Vote.query.filter_by(post_id=post_id, value=-1).count()
        vote_score = upvotes - downvotes
        
        # Get user's vote if authenticated
        user_vote = None
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                user_vote_obj = Vote.query.filter_by(post_id=post_id, user_id=user_id).first()
                user_vote = user_vote_obj.value if user_vote_obj else None
        except:
            pass
        
        return jsonify({
            "post_id": post_id,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "vote_score": vote_score,
            "total_votes": upvotes + downvotes,
            "user_vote": user_vote
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting votes for post {post_id}: {e}")
        return jsonify({"error": "Failed to get vote information"}), 500

@vote_bp.route("/votes/comment/<int:comment_id>", methods=["GET"])
def get_comment_votes(comment_id):
    """Get vote information for a comment"""
    try:
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        upvotes = Vote.query.filter_by(comment_id=comment_id, value=1).count()
        downvotes = Vote.query.filter_by(comment_id=comment_id, value=-1).count()
        vote_score = upvotes - downvotes
        
        # Get user's vote if authenticated
        user_vote = None
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                user_vote_obj = Vote.query.filter_by(comment_id=comment_id, user_id=user_id).first()
                user_vote = user_vote_obj.value if user_vote_obj else None
        except:
            pass
        
        return jsonify({
            "comment_id": comment_id,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "vote_score": vote_score,
            "total_votes": upvotes + downvotes,
            "user_vote": user_vote
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting votes for comment {comment_id}: {e}")
        return jsonify({"error": "Failed to get vote information"}), 500

# Admin endpoints for vote management
@vote_bp.route("/votes/post/<int:post_id>/reset", methods=["DELETE"])
@jwt_required()
def reset_post_votes(post_id):
    """Reset all votes for a post (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Delete all votes for this post
        deleted_count = Vote.query.filter_by(post_id=post_id).count()
        Vote.query.filter_by(post_id=post_id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Reset {deleted_count} votes for post",
            "deleted_votes": deleted_count,
            "post_id": post_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting votes for post {post_id}: {e}")
        return jsonify({"error": "Failed to reset votes"}), 500

@vote_bp.route("/votes/comment/<int:comment_id>/reset", methods=["DELETE"])
@jwt_required()
def reset_comment_votes(comment_id):
    """Reset all votes for a comment (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403
        
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Delete all votes for this comment
        deleted_count = Vote.query.filter_by(comment_id=comment_id).count()
        Vote.query.filter_by(comment_id=comment_id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Reset {deleted_count} votes for comment",
            "deleted_votes": deleted_count,
            "comment_id": comment_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting votes for comment {comment_id}: {e}")
        return jsonify({"error": "Failed to reset votes"}), 500