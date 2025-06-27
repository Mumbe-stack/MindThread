from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Post, Comment, Vote
from datetime import datetime
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

# FIXED: Remove url_prefix since app.py now handles it
vote_bp = Blueprint("votes", __name__)


@vote_bp.route("/votes/post", methods=["POST"])
@jwt_required()
@block_check_required 
def vote_post():
    """Vote on a post (upvote/downvote) - users can vote on any post including their own"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        post_id = data.get("post_id")
        value = data.get("value")

        # Enhanced validation
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if post_id is None:
            return jsonify({"error": "post_id is required"}), 400
            
        if value not in [-1, 1]:
            return jsonify({"error": "value must be 1 (upvote) or -1 (downvote)"}), 400

        # Validate post exists
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Check if post is approved
        if not post.is_approved:
            return jsonify({"error": "Cannot vote on unapproved post"}), 403

        # Check if user already voted on this post
        existing_vote = Vote.query.filter_by(user_id=user_id, post_id=post_id).first()
        
        if existing_vote:
            if existing_vote.value == value:
                # Same vote - remove it (toggle off)
                db.session.delete(existing_vote)
                msg = "Vote removed"
                user_vote = None
            else:
                # Different vote - update it
                existing_vote.value = value 
                existing_vote.created_at = datetime.utcnow()  # Update timestamp
                msg = "Vote updated"
                user_vote = value
        else:
            # New vote
            vote = Vote(
                user_id=user_id, 
                post_id=post_id, 
                value=value,
                created_at=datetime.utcnow()
            )
            db.session.add(vote)
            msg = "Vote recorded"
            user_vote = value

        db.session.commit()
        
        # Get updated score - more efficient query
        votes = Vote.query.filter_by(post_id=post_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        logger.info(f"User {user_id} voted {value} on post {post_id}")

        return jsonify({
            "success": True,
            "message": msg,
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error voting on post: {e}")
        return jsonify({"error": "Failed to record vote"}), 500


@vote_bp.route("/votes/post/<int:post_id>/score", methods=["GET"])
def get_post_score(post_id):
    """Get voting statistics for a post"""
    try:
        # Check if user is authenticated (optional for viewing scores)
        current_user_id = None
        user_vote = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        votes = Vote.query.filter_by(post_id=post_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        # Get user's vote if authenticated
        if current_user_id:
            user_vote_obj = Vote.query.filter_by(
                user_id=current_user_id, 
                post_id=post_id
            ).first()
            user_vote = user_vote_obj.value if user_vote_obj else None

        return jsonify({
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        logger.error(f"Error getting post score: {e}")
        return jsonify({"error": "Failed to get post score"}), 500


@vote_bp.route("/votes/comment", methods=["POST"])
@jwt_required()
@block_check_required  
def vote_comment():
    """Vote on a comment (upvote/downvote) - users can vote on any comment including their own"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        comment_id = data.get("comment_id")
        value = data.get("value")

        if not data:
            return jsonify({"error": "No data provided"}), 400
       
        if comment_id is None:
            return jsonify({"error": "comment_id is required"}), 400
            
        if value not in [-1, 1]:
            return jsonify({"error": "value must be 1 (upvote) or -1 (downvote)"}), 400

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": f"Comment with ID {comment_id} does not exist"}), 404

        # Check if comment is approved
        if not comment.is_approved:
            return jsonify({"error": "Cannot vote on unapproved comment"}), 403
       
        existing_vote = Vote.query.filter_by(user_id=user_id, comment_id=comment_id).first()

        if existing_vote:
            if existing_vote.value == value:
                # Same vote - remove it (toggle off)
                db.session.delete(existing_vote)
                msg = "Vote removed"
                user_vote = None
            else:
                # Different vote - update it
                existing_vote.value = value
                existing_vote.created_at = datetime.utcnow()
                msg = "Vote updated"
                user_vote = value
        else:
            # New vote
            new_vote = Vote(
                user_id=user_id, 
                comment_id=comment_id, 
                value=value,
                created_at=datetime.utcnow()
            )
            db.session.add(new_vote)
            msg = "Vote recorded"
            user_vote = value

        db.session.commit()

        # Get updated score
        votes = Vote.query.filter_by(comment_id=comment_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        logger.info(f"User {user_id} voted {value} on comment {comment_id}")

        return jsonify({
            "success": True,
            "message": msg,
            "comment_id": comment_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error voting on comment: {e}")
        return jsonify({"error": "Failed to record vote"}), 500


@vote_bp.route("/votes/comment/<int:comment_id>/score", methods=["GET"])
def get_comment_score(comment_id):
    """Get voting statistics for a comment"""
    try:
        # Check if user is authenticated (optional)
        current_user_id = None
        user_vote = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        votes = Vote.query.filter_by(comment_id=comment_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        # Get user's vote if authenticated
        if current_user_id:
            user_vote_obj = Vote.query.filter_by(
                user_id=current_user_id, 
                comment_id=comment_id
            ).first()
            user_vote = user_vote_obj.value if user_vote_obj else None

        return jsonify({
            "comment_id": comment_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        logger.error(f"Error getting comment score: {e}")
        return jsonify({"error": "Failed to get comment score"}), 500


@vote_bp.route("/votes/user/<int:user_id>/votes", methods=["GET"])
@jwt_required()
def get_user_votes(user_id):
    """Get current user's votes for posts and comments (for showing vote status)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only allow users to see their own votes, or admins can see any
        if current_user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "Access denied"}), 403

        votes = Vote.query.filter_by(user_id=user_id).all()
        
        post_votes = {}
        comment_votes = {}
        
        for vote in votes:
            if vote.post_id:
                post_votes[vote.post_id] = vote.value
            elif vote.comment_id:
                comment_votes[vote.comment_id] = vote.value

        return jsonify({
            "user_id": user_id,
            "post_votes": post_votes,
            "comment_votes": comment_votes,
            "total_votes": len(votes)
        }), 200

    except Exception as e:
        logger.error(f"Error getting user votes: {e}")
        return jsonify({"error": "Failed to get user votes"}), 500


@vote_bp.route("/votes/post/<int:post_id>", methods=["DELETE"])
@jwt_required()
@block_check_required  
def delete_vote_on_post(post_id):
    """Delete user's own vote on a post"""
    try:
        user_id = get_jwt_identity()

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": f"Post ID {post_id} does not exist"}), 404

        vote = Vote.query.filter_by(user_id=user_id, post_id=post_id).first()
        if not vote:
            return jsonify({"error": f"No vote found for this post by the user"}), 404

        db.session.delete(vote)
        db.session.commit()

        # Get updated score
        votes = Vote.query.filter_by(post_id=post_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])

        logger.info(f"User {user_id} deleted vote on post {post_id}")

        return jsonify({
            "success": True,
            "message": f"Vote on Post ID {post_id} deleted successfully",
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting vote on post: {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


@vote_bp.route("/votes/comment/<int:comment_id>", methods=["DELETE"])
@jwt_required()
@block_check_required 
def delete_comment_vote(comment_id):
    """Delete user's own vote on a comment"""
    try:
        user_id = get_jwt_identity()

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        vote = Vote.query.filter_by(user_id=user_id, comment_id=comment_id).first()
        if not vote:
            return jsonify({"error": "No vote found for this comment"}), 404

        db.session.delete(vote)
        db.session.commit()

        # Get updated score
        votes = Vote.query.filter_by(comment_id=comment_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])

        logger.info(f"User {user_id} deleted vote on comment {comment_id}")

        return jsonify({
            "success": True,
            "message": "Vote on comment removed",
            "comment_id": comment_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment vote: {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


# ADMIN SUPERPOWER ROUTES
@vote_bp.route("/votes/admin/post/<int:post_id>/votes", methods=["GET"])
@jwt_required()
def admin_get_post_votes(post_id):
    """Admin: Get all votes on a specific post with user details"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        votes = Vote.query.filter_by(post_id=post_id).join(User).all()
        
        vote_details = []
        for vote in votes:
            vote_details.append({
                "id": vote.id,
                "value": vote.value,
                "user_id": vote.user_id,
                "username": vote.user.username,
                "created_at": vote.created_at.isoformat() if hasattr(vote, 'created_at') and vote.created_at else None
            })

        return jsonify({
            "post_id": post_id,
            "post_title": post.title,
            "votes": vote_details,
            "total_votes": len(vote_details),
            "upvotes": len([v for v in votes if v.value == 1]),
            "downvotes": len([v for v in votes if v.value == -1]),
            "score": sum(v.value for v in votes)
        }), 200

    except Exception as e:
        logger.error(f"Error getting post votes (admin): {e}")
        return jsonify({"error": "Failed to get post votes"}), 500


@vote_bp.route("/votes/admin/vote/<int:vote_id>", methods=["DELETE"])
@jwt_required()
def admin_delete_vote(vote_id):
    """Admin: Delete any vote"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        vote = Vote.query.get(vote_id)
        if not vote:
            return jsonify({"error": "Vote not found"}), 404

        vote_info = {
            "id": vote.id,
            "user_id": vote.user_id,
            "post_id": vote.post_id,
            "comment_id": vote.comment_id,
            "value": vote.value
        }

        db.session.delete(vote)
        db.session.commit()

        logger.info(f"Admin {current_user.id} deleted vote {vote_id}")

        return jsonify({
            "success": True,
            "message": "Vote deleted by admin",
            "deleted_vote": vote_info
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting vote (admin): {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


@vote_bp.route("/votes/admin/reset/post/<int:post_id>", methods=["DELETE"])
@jwt_required()
def admin_reset_post_votes(post_id):
    """Admin: Delete all votes on a specific post"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        votes = Vote.query.filter_by(post_id=post_id).all()
        vote_count = len(votes)

        for vote in votes:
            db.session.delete(vote)

        db.session.commit()

        logger.info(f"Admin {current_user.id} reset all votes for post {post_id}")

        return jsonify({
            "success": True,
            "message": f"All votes reset for post '{post.title}'",
            "post_id": post_id,
            "votes_deleted": vote_count
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting post votes (admin): {e}")
        return jsonify({"error": "Failed to reset post votes"}), 500


@vote_bp.route("/votes/admin/comment/<int:comment_id>/votes", methods=["GET"])
@jwt_required()
def admin_get_comment_votes(comment_id):
    """Admin: Get all votes on a specific comment with user details"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        votes = Vote.query.filter_by(comment_id=comment_id).join(User).all()
        
        vote_details = []
        for vote in votes:
            vote_details.append({
                "id": vote.id,
                "value": vote.value,
                "user_id": vote.user_id,
                "username": vote.user.username,
                "created_at": vote.created_at.isoformat() if hasattr(vote, 'created_at') and vote.created_at else None
            })

        return jsonify({
            "comment_id": comment_id,
            "comment_content": comment.content[:100] + "..." if len(comment.content) > 100 else comment.content,
            "votes": vote_details,
            "total_votes": len(vote_details),
            "upvotes": len([v for v in votes if v.value == 1]),
            "downvotes": len([v for v in votes if v.value == -1]),
            "score": sum(v.value for v in votes)
        }), 200

    except Exception as e:
        logger.error(f"Error getting comment votes (admin): {e}")
        return jsonify({"error": "Failed to get comment votes"}), 500


def serialize_vote(vote):
    """Helper method for Vote model serialization"""
    return {
        "id": vote.id,
        "value": vote.value,
        "user_id": vote.user_id,
        "post_id": vote.post_id,
        "comment_id": vote.comment_id,
        "created_at": vote.created_at.isoformat() if hasattr(vote, 'created_at') and vote.created_at else None
    }