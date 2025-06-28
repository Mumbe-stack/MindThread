from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Post, Comment, Vote
from .utils import block_check_required  

vote_bp = Blueprint("vote_bp", __name__, url_prefix="/api/votes")


@vote_bp.route("/post", methods=["POST"])
@jwt_required()
@block_check_required 
def vote_post():
    """Vote on a post (upvote/downvote) - users can vote on any post including their own"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        post_id = data.get("post_id")
        value = data.get("value")

        if post_id is None or value not in [-1, 1]:
            return jsonify({"error": "post_id and value (1 or -1) are required"}), 400

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

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
                msg = "Vote updated"
                user_vote = value
        else:
            # New vote
            vote = Vote(user_id=user_id, post_id=post_id, value=value)
            db.session.add(vote)
            msg = "Vote recorded"
            user_vote = value

        db.session.commit()
        
        # Get updated score
        votes = Vote.query.filter_by(post_id=post_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])

        return jsonify({
            "success": True,
            "message": msg,
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error voting on post: {e}")
        return jsonify({"error": "Failed to record vote"}), 500


@vote_bp.route("/post/<int:post_id>/score", methods=["GET"])
def get_post_score(post_id):
    """Get voting statistics for a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        votes = Vote.query.filter_by(post_id=post_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        return jsonify({
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting post score: {e}")
        return jsonify({"error": "Failed to get post score"}), 500


@vote_bp.route("/comment", methods=["POST"])
@jwt_required()
@block_check_required  
def vote_comment():
    """Vote on a comment (upvote/downvote) - users can vote on any comment including their own"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        comment_id = data.get("comment_id")
        value = data.get("value")
       
        if comment_id is None or value not in [-1, 1]:
            return jsonify({"error": "Valid 'comment_id' and 'value' (1 for upvote, -1 for downvote) are required"}), 400

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": f"Comment with ID {comment_id} does not exist"}), 404
       
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
                msg = "Vote updated"
                user_vote = value
        else:
            # New vote
            new_vote = Vote(user_id=user_id, comment_id=comment_id, value=value)
            db.session.add(new_vote)
            msg = "Vote recorded"
            user_vote = value

        db.session.commit()

        # Get updated score
        votes = Vote.query.filter_by(comment_id=comment_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])

        return jsonify({
            "success": True,
            "message": msg,
            "comment_id": comment_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "user_vote": user_vote
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error voting on comment: {e}")
        return jsonify({"error": "Failed to record vote"}), 500


@vote_bp.route("/comment/<int:comment_id>/score", methods=["GET"])
def get_comment_score(comment_id):
    """Get voting statistics for a comment"""
    try:
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        votes = Vote.query.filter_by(comment_id=comment_id).all()
        score = sum(v.value for v in votes)
        upvotes = len([v for v in votes if v.value == 1])
        downvotes = len([v for v in votes if v.value == -1])
        total_votes = len(votes)

        return jsonify({
            "comment_id": comment_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total_votes": total_votes
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting comment score: {e}")
        return jsonify({"error": "Failed to get comment score"}), 500


@vote_bp.route("/user/<int:user_id>/votes", methods=["GET"])
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
            "comment_votes": comment_votes
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting user votes: {e}")
        return jsonify({"error": "Failed to get user votes"}), 500


@vote_bp.route("/post/<int:post_id>", methods=["DELETE"])
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

        return jsonify({
            "success": True,
            "message": f"Vote on Post ID {post_id} deleted successfully",
            "post_id": post_id,
            "new_score": score
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting vote on post: {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


@vote_bp.route("/comment/<int:comment_id>", methods=["DELETE"])
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

        return jsonify({
            "success": True,
            "message": "Vote on comment removed",
            "comment_id": comment_id,
            "new_score": score
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment vote: {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


# ADMIN SUPERPOWER ROUTES
@vote_bp.route("/admin/post/<int:post_id>/votes", methods=["GET"])
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
                "created_at": vote.created_at.isoformat() if hasattr(vote, 'created_at') else None
            })

        return jsonify({
            "post_id": post_id,
            "post_title": post.title,
            "votes": vote_details,
            "total_votes": len(vote_details),
            "upvotes": len([v for v in votes if v.value == 1]),
            "downvotes": len([v for v in votes if v.value == -1])
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting post votes (admin): {e}")
        return jsonify({"error": "Failed to get post votes"}), 500


@vote_bp.route("/admin/vote/<int:vote_id>", methods=["DELETE"])
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

        db.session.delete(vote)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Vote deleted by admin"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting vote (admin): {e}")
        return jsonify({"error": "Failed to delete vote"}), 500


@vote_bp.route("/admin/reset/post/<int:post_id>", methods=["DELETE"])
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

        return jsonify({
            "success": True,
            "message": f"All votes reset for post '{post.title}'",
            "post_id": post_id,
            "votes_deleted": vote_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting post votes (admin): {e}")
        return jsonify({"error": "Failed to reset post votes"}), 500


def to_dict(self):
    """Helper method for Vote model serialization"""
    return {
        "id": self.id,
        "value": self.value,
        "user_id": self.user_id,
        "post_id": self.post_id,
        "comment_id": self.comment_id,
        "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') else None
    }