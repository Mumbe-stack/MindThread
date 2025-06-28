from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Post, Vote
from datetime import datetime, timezone
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

vote_bp = Blueprint("votes", __name__)

@vote_bp.route("/votes/post", methods=["POST"])
@jwt_required()
@block_check_required 
def vote_post():
    """Vote on a post (upvote/downvote) - POSTS ONLY"""
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

        # Check if post is approved (unless user is admin or post author)
        current_user = User.query.get(user_id)
        if not post.is_approved and not (current_user and current_user.is_admin) and post.user_id != user_id:
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
                existing_vote.created_at = datetime.now(timezone.utc)
                msg = "Vote updated"
                user_vote = value
        else:
            # New vote
            vote = Vote(
                user_id=user_id, 
                post_id=post_id, 
                value=value,
                created_at=datetime.now(timezone.utc)
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
        return jsonify({"error": "Failed to record vote", "message": str(e)}), 500

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

@vote_bp.route("/votes/user/<int:user_id>/votes", methods=["GET"])
@jwt_required()
def get_user_votes(user_id):
    """Get current user's votes for posts (for showing vote status) - POSTS ONLY"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only allow users to see their own votes, or admins can see any
        if current_user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "Access denied"}), 403

        # Only get post votes (no comment votes)
        votes = Vote.query.filter_by(user_id=user_id).filter(Vote.post_id.isnot(None)).all()
        
        post_votes = {}
        
        for vote in votes:
            post_votes[vote.post_id] = vote.value

        return jsonify({
            "user_id": user_id,
            "post_votes": post_votes,
            "total_votes": len(votes),
            "comment_voting_disabled": True
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
        total_votes = len(votes)

        logger.info(f"User {user_id} deleted vote on post {post_id}")

        return jsonify({
            "success": True,
            "message": f"Vote on Post ID {post_id} deleted successfully",
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting vote on post: {e}")
        return jsonify({"error": "Failed to delete vote"}), 500

# ADMIN ROUTES - POSTS ONLY
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
    """Admin: Delete any vote (POSTS ONLY)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        vote = Vote.query.get(vote_id)
        if not vote:
            return jsonify({"error": "Vote not found"}), 404

        # Ensure this is a post vote only
        if not vote.post_id:
            return jsonify({"error": "Invalid vote type"}), 400

        vote_info = {
            "id": vote.id,
            "user_id": vote.user_id,
            "post_id": vote.post_id,
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

@vote_bp.route("/votes/admin/stats", methods=["GET"])
@jwt_required()
def admin_get_voting_stats():
    """Admin: Get comprehensive voting statistics - POSTS ONLY"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        # Get all votes (should only be post votes now)
        total_votes = Vote.query.count()
        total_upvotes = Vote.query.filter_by(value=1).count()
        total_downvotes = Vote.query.filter_by(value=-1).count()
        
        # Posts with votes
        posts_with_votes = Vote.query.with_entities(Vote.post_id).distinct().count()
        
        # Total posts
        total_posts = Post.query.count()
        
        # Voting participation rate
        participation_rate = round((posts_with_votes / total_posts * 100) if total_posts > 0 else 0, 1)
        
        return jsonify({
            "total_votes": total_votes,
            "total_upvotes": total_upvotes,
            "total_downvotes": total_downvotes,
            "posts_with_votes": posts_with_votes,
            "total_posts": total_posts,
            "participation_rate": participation_rate,
            "vote_types": ["post"],  # Only posts now
            "comment_voting_disabled": True,
            "features": {
                "post_voting": True,
                "comment_voting": False,
                "admin_vote_management": True
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting voting stats (admin): {e}")
        return jsonify({"error": "Failed to get voting statistics"}), 500

@vote_bp.route("/votes/admin/users/top-voters", methods=["GET"])
@jwt_required()
def admin_get_top_voters():
    """Admin: Get users with most voting activity - POSTS ONLY"""
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        # Get top voters by vote count
        from sqlalchemy import func
        top_voters = db.session.query(
            Vote.user_id,
            User.username,
            func.count(Vote.id).label('vote_count'),
            func.sum(func.case([(Vote.value == 1, 1)], else_=0)).label('upvotes'),
            func.sum(func.case([(Vote.value == -1, 1)], else_=0)).label('downvotes')
        ).join(User, Vote.user_id == User.id)\
         .group_by(Vote.user_id, User.username)\
         .order_by(func.count(Vote.id).desc())\
         .limit(10).all()
        
        top_voters_data = []
        for voter in top_voters:
            top_voters_data.append({
                "user_id": voter.user_id,
                "username": voter.username,
                "total_votes": voter.vote_count,
                "upvotes": voter.upvotes,
                "downvotes": voter.downvotes
            })
        
        return jsonify({
            "top_voters": top_voters_data,
            "limit": 10
        }), 200

    except Exception as e:
        logger.error(f"Error getting top voters (admin): {e}")
        return jsonify({"error": "Failed to get top voters"}), 500

# Test endpoint to verify voting system
@vote_bp.route("/votes/test", methods=["GET"])
def test_votes():
    """Test endpoint to verify vote system is working - POSTS ONLY"""
    try:
        vote_count = Vote.query.count()
        post_votes = Vote.query.filter(Vote.post_id.isnot(None)).count()
        
        # Verify no comment votes exist
        comment_votes_check = Vote.query.filter(Vote.post_id.is_(None)).count()
        
        return jsonify({
            "success": True,
            "message": "Vote system is working (POST VOTING ONLY)",
            "total_votes": vote_count,
            "post_votes": post_votes,
            "comment_votes": 0,  # Always 0 now
            "invalid_votes": comment_votes_check,  # Should be 0
            "features": {
                "post_voting": True,
                "comment_voting": False,  # Disabled
                "admin_vote_management": True
            },
            "endpoints": {
                "vote_on_post": "POST /api/votes/post",
                "get_post_score": "GET /api/votes/post/<id>/score",
                "get_user_votes": "GET /api/votes/user/<id>/votes",
                "delete_post_vote": "DELETE /api/votes/post/<id>",
                "admin_get_post_votes": "GET /api/votes/admin/post/<id>/votes",
                "admin_delete_vote": "DELETE /api/votes/admin/vote/<id>",
                "admin_reset_post_votes": "DELETE /api/votes/admin/reset/post/<id>",
                "admin_voting_stats": "GET /api/votes/admin/stats",
                "admin_top_voters": "GET /api/votes/admin/users/top-voters"
            },
            "removed_endpoints": [
                "POST /api/votes/comment",
                "GET /api/votes/comment/<id>/score", 
                "DELETE /api/votes/comment/<id>",
                "GET /api/votes/admin/comment/<id>/votes"
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in vote test endpoint: {e}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500

def serialize_vote(vote):
    """Helper method for Vote model serialization - POSTS ONLY"""
    return {
        "id": vote.id,
        "value": vote.value,
        "user_id": vote.user_id,
        "post_id": vote.post_id,
        "created_at": vote.created_at.isoformat() if hasattr(vote, 'created_at') and vote.created_at else None
    }