from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Comment, User
from datetime import datetime

comment_bp = Blueprint('comment_bp', __name__, url_prefix="/api/comments")

# ✅ Public: List all comments, filterable by post_id or user_id
@comment_bp.route("/", methods=["GET"])
def list_comments():
    post_id = request.args.get("post_id")
    user_id = request.args.get("user_id")

    query = Comment.query
    if post_id:
        query = query.filter_by(post_id=post_id)
    if user_id:
        query = query.filter_by(user_id=user_id)

    comments = query.order_by(Comment.created_at.desc()).all()

    return jsonify([
        {
            "id": c.id,
            "content": c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "parent_id": c.parent_id,
            "created_at": c.created_at.isoformat()
        } for c in comments
    ]), 200

# ✅ JWT: Create comment or threaded reply
@comment_bp.route("/", methods=["POST"])
@jwt_required()
def create_comment():
    data = request.get_json()
    current_user_id = get_jwt_identity()

    if not all(k in data for k in ("content", "post_id")):
        return jsonify({"error": "Missing fields: content, post_id"}), 400

    new_comment = Comment(
        content=data["content"],
        post_id=data["post_id"],
        user_id=current_user_id,
        parent_id=data.get("parent_id"),  # Optional threaded reply
        created_at=datetime.utcnow()
    )
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({
        "success": "Comment created",
        "comment_id": new_comment.id
    }), 201

# ✅ JWT: Update comment (only owner can update)
@comment_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def update_comment(id):
    current_user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)

    if comment.user_id != current_user_id:
        return jsonify({"error": "You are not authorized to edit this comment"}), 403

    data = request.get_json()
    if not data.get("content"):
        return jsonify({"error": "Content is required"}), 400

    old_content = comment.content
    comment.content = data["content"]
    db.session.commit()

    return jsonify({
        "success": "Comment updated",
        "old_content": old_content,
        "new_content": comment.content
    }), 200

# ✅ JWT: Delete own comment
@comment_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_comment(id):
    current_user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)

    if comment.user_id != current_user_id:
        return jsonify({"error": "You are not authorized to delete this comment"}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} deleted"}), 200

# ✅ Admin-only: Force delete any comment
@comment_bp.route("/<int:id>/force", methods=["DELETE"])
@jwt_required()
def force_delete_comment(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} forcibly deleted by admin"}), 200

# ✅ Admin-only: Flag comment
@comment_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
def flag_comment(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    comment = Comment.query.get_or_404(id)
    comment.flagged = True  # Make sure this field exists in your model
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} flagged for review"}), 200
