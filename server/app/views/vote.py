from flask import Blueprint, request, jsonify
from ..models import Vote, db

vote_bp = Blueprint('vote_bp', __name__)

def validate_vote_input(data):
    if "user_id" not in data or "value" not in data:
        return False, {"error": "user_id and value are required"}, 400
    return True, None, None

@vote_bp.route("/post/<int:post_id>", methods=["POST"])
def vote_post(post_id):
    data = request.json
    valid, error_response, status_code = validate_vote_input(data)
    if not valid:
        return jsonify(error_response), status_code

    existing_vote = Vote.query.filter_by(user_id=data["user_id"], post_id=post_id).first()
    if existing_vote:
        return jsonify({"error": "You have already voted on this post"}), 409

    vote = Vote(user_id=data["user_id"], post_id=post_id, value=data["value"])
    db.session.add(vote)
    db.session.commit()

    return jsonify({"success": "Vote recorded", "vote_id": vote.id}), 201

@vote_bp.route("/post/<int:post_id>", methods=["DELETE"])
def delete_vote_post(post_id):
    data = request.json
    if "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    vote = Vote.query.filter_by(user_id=data["user_id"], post_id=post_id).first()
    if not vote:
        return jsonify({"error": "No vote found for this post by the user"}), 404

    db.session.delete(vote)
    db.session.commit()
    return jsonify({"success": "Vote on post removed"}), 200

@vote_bp.route("/comment/<int:comment_id>", methods=["POST"])
def vote_comment(comment_id):
    data = request.json
    valid, error_response, status_code = validate_vote_input(data)
    if not valid:
        return jsonify(error_response), status_code

    existing_vote = Vote.query.filter_by(user_id=data["user_id"], comment_id=comment_id).first()
    if existing_vote:
        return jsonify({"error": "You have already voted on this comment"}), 409

    vote = Vote(user_id=data["user_id"], comment_id=comment_id, value=data["value"])
    db.session.add(vote)
    db.session.commit()

    return jsonify({"success": "Vote recorded", "vote_id": vote.id}), 201

@vote_bp.route("/comment/<int:comment_id>", methods=["DELETE"])
def delete_vote_comment(comment_id):
    data = request.json
    if "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    vote = Vote.query.filter_by(user_id=data["user_id"], comment_id=comment_id).first()
    if not vote:
        return jsonify({"error": "No vote found for this comment by the user"}), 404

    db.session.delete(vote)
    db.session.commit()
    return jsonify({"success": "Vote on comment removed"}), 200
