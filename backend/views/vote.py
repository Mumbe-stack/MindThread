from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Post, Comment, Vote
from .utils import block_check_required  

vote_bp = Blueprint("vote_bp", __name__, url_prefix="/api/votes")


@vote_bp.route("/post", methods=["POST"])
@jwt_required()
@block_check_required 
def vote_post():
    data = request.get_json()
    user_id = get_jwt_identity()
    post_id = data.get("post_id")
    value = data.get("value")

    if post_id is None or value not in [-1, 1]:
        return jsonify({"error": "post_id and value (1 or -1) are required"}), 400

    if not Post.query.get(post_id):
        return jsonify({"error": "Post not found"}), 404

    vote = Vote.query.filter_by(user_id=user_id, post_id=post_id).first()
    if vote:
        vote.value = value 
        msg = "Vote updated"
    else:
        vote = Vote(user_id=user_id, post_id=post_id, value=value)
        db.session.add(vote)
        msg = "Vote recorded"

    db.session.commit()
    return jsonify({"success": msg}), 200


@vote_bp.route("/post/<int:post_id>/score", methods=["GET"])
def get_post_score(post_id):
    votes = Vote.query.filter_by(post_id=post_id).all()
    score = sum(v.value for v in votes)
    return jsonify({"post_id": post_id, "score": score}), 200


@vote_bp.route("/comment", methods=["POST"])
@jwt_required()
@block_check_required  
def vote_comment():
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
        existing_vote.value = value
        message = "Vote updated"
    else:
        new_vote = Vote(user_id=user_id, comment_id=comment_id, value=value)
        db.session.add(new_vote)
        message = "Vote recorded"

    db.session.commit()

    return jsonify({
        "success": message,
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "created_at": comment.created_at.isoformat()
        }
    }), 200


@vote_bp.route("/comment/<int:comment_id>/score", methods=["GET"])
def get_comment_score(comment_id):
    votes = Vote.query.filter_by(comment_id=comment_id).all()
    score = sum(v.value for v in votes)
    return jsonify({"comment_id": comment_id, "score": score}), 200


@vote_bp.route("/post/<int:post_id>", methods=["DELETE"])
@jwt_required()
@block_check_required  
def delete_vote_on_post(post_id):
    user_id = get_jwt_identity()

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": f"Post ID {post_id} does not exist"}), 404

    vote = Vote.query.filter_by(user_id=user_id, post_id=post_id).first()
    if not vote:
        return jsonify({"error": f"No vote found for this post by the user"}), 404

    db.session.delete(vote)
    db.session.commit()

    return jsonify({"success": f"Vote on Post ID {post_id} deleted successfully"}), 200


@vote_bp.route("/comment/<int:comment_id>", methods=["DELETE"])
@jwt_required()
@block_check_required 
def delete_comment_vote(comment_id):
    user_id = get_jwt_identity()

    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    vote = Vote.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    if not vote:
        return jsonify({"error": "No vote found for this comment"}), 404

    db.session.delete(vote)
    db.session.commit()

    return jsonify({"success": "Vote on comment removed"}), 200


def to_dict(self):
    return {
        "id": self.id,
        "value": self.value,
        "user_id": self.user_id,
        "post_id": self.post_id,
        "comment_id": self.comment_id
    }
