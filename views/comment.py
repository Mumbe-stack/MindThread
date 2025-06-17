from flask import Blueprint, request, jsonify
from ..routes.models import Comment, db
from datetime import datetime

comment_bp = Blueprint('comment_bp', __name__)

@comment_bp.route("/", methods=["GET"])
def list_comments():
    comments = Comment.query.all()
    return jsonify([
        {
            "id": c.id,
            "content": c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at
        } for c in comments
    ]), 200

@comment_bp.route("/", methods=["POST"])
def create_comment():
    data = request.json

    if not all(k in data for k in ("content", "user_id", "post_id")):
        return jsonify({"error": "Missing required fields: content, user_id, post_id"}), 400

    existing = Comment.query.filter_by(
        user_id=data["user_id"],
        post_id=data["post_id"],
        content=data["content"]
    ).first()

    if existing:
        return jsonify({"error": "Duplicate comment exists"}), 409

    new_comment = Comment(
        content=data["content"],
        user_id=data["user_id"],
        post_id=data["post_id"],
        created_at=datetime.utcnow()
    )
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({
        "success": "Comment created",
        "id": new_comment.id
    }), 201

@comment_bp.route("/<int:id>", methods=["PUT"])
def update_comment(id):
    comment = Comment.query.get_or_404(id)
    data = request.json

    old_content = comment.content
    comment.content = data.get("content", comment.content)
    db.session.commit()

    return jsonify({
        "success": "Comment updated",
        "old_content": old_content,
        "new_content": comment.content
    }), 200


@comment_bp.route("/<int:id>", methods=["DELETE"])
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()

    return jsonify({
        "success": f"Comment ID {id} deleted"
    }), 200
