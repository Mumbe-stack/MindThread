from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Comment, User, Post
from datetime import datetime
from .utils import block_check_required 

comment_bp = Blueprint('comment_bp', __name__, url_prefix="/api/comments")


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


@comment_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required
def create_comment():
    data = request.get_json()
    user_id = get_jwt_identity()

    if not data.get("content") or not data.get("post_id"):
        return jsonify({"error": "Missing fields: content and post_id are required"}), 400

    post = Post.query.get(data["post_id"])
    if not post:
        return jsonify({"error": f"Post with ID {data['post_id']} does not exist"}), 404

    parent_id = data.get("parent_id")
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if not parent_comment:
            return jsonify({"error": f"Parent comment with ID {parent_id} does not exist"}), 404

    comment = Comment(
        content=data["content"],
        post_id=data["post_id"],
        user_id=user_id,
        parent_id=parent_id,
        created_at=datetime.utcnow()
    )

    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "success": "Comment created",
        "comment_id": comment.id,
        "is_reply_to": parent_id
    }), 201


@comment_bp.route("/<int:comment_id>/like/", methods=["POST", "OPTIONS"])
def like_comment(comment_id):
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    from flask_jwt_extended import verify_jwt_in_request

    
    verify_jwt_in_request()
    user_id = get_jwt_identity()
    
    comment = Comment.query.get_or_404(comment_id)
    user = User.query.get_or_404(user_id)

    if comment in user.liked_comments:
        user.liked_comments.remove(comment)  
        db.session.commit()
        return jsonify({
            "message": f"Comment ID {comment_id} unliked",
            "likes": comment.likes,
            "liked_by": [u.id for u in comment.liked_by_users]
        }), 200
    else:
        user.liked_comments.append(comment)  
        db.session.commit()
        return jsonify({
            "message": f"Comment ID {comment_id} liked",
            "likes": comment.likes,
            "liked_by": [u.id for u in comment.liked_by_users]
        }), 200


@comment_bp.route("/<int:id>/unlike", methods=["PATCH"])
@jwt_required()
@block_check_required
def unlike_comment(id):
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)
    user = User.query.get(user_id)

    if comment not in user.liked_comments:
        return jsonify({"error": "You haven't liked this comment yet"}), 400

    user.liked_comments.remove(comment)
    db.session.commit()

    return jsonify({
        "message": f"Comment ID {id} unliked",
        "likes": comment.likes,
        "unliked_by": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }), 200


@comment_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
@block_check_required
def update_comment(id):
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)

    if comment.user_id != user_id:
        return jsonify({"error": "You can only edit your own comment"}), 403

    data = request.get_json()
    if not data.get("content"):
        return jsonify({"error": "Content is required"}), 400

    comment.content = data["content"]
    db.session.commit()

    return jsonify({
        "success": "Comment updated",
        "new_content": comment.content
    }), 200


@comment_bp.route("/<int:parent_id>/replies", methods=["GET"])
def get_replies(parent_id):
    parent = Comment.query.get(parent_id)
    if not parent:
        return jsonify({"error": f"Comment with ID {parent_id} does not exist"}), 404

    replies = Comment.query.filter_by(parent_id=parent_id).order_by(Comment.created_at.asc()).all()
    if not replies:
        return jsonify({"error": f"No replies found for comment ID {parent_id}"}), 404

    return jsonify([
        {
            "id": reply.id,
            "content": reply.content,
            "post_id": reply.post_id,
            "user_id": reply.user_id,
            "parent_id": reply.parent_id,
            "created_at": reply.created_at.isoformat()
        } for reply in replies
    ]), 200


@comment_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_comment(id):
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)

    if comment.user_id != user_id:
        return jsonify({"error": "You can only delete your own comment"}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} deleted successfully"}), 200


@comment_bp.route("/<int:id>/force", methods=["DELETE"])
@jwt_required()
@block_check_required
def force_delete_comment(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} forcibly deleted by admin"}), 200


@comment_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
@block_check_required
def flag_comment(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    comment = Comment.query.get_or_404(id)
    comment.is_flagged = True  
    db.session.commit()

    return jsonify({"success": f"Comment ID {id} flagged for review"}), 200


@comment_bp.route("/<int:id>/approve", methods=["PATCH"])
@jwt_required()
@block_check_required
def set_comment_approval(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    comment = Comment.query.get_or_404(id)
    data = request.get_json()

    if "is_approved" not in data:
        return jsonify({"error": "Missing 'is_approved' field"}), 400

    comment.is_approved = bool(data["is_approved"])
    db.session.commit()

    status = "approved" if comment.is_approved else "rejected"
    return jsonify({"success": f"Comment ID {id} {status}"}), 200


def to_dict(self):
    return {
        "id": self.id,
        "content": self.content,
        "created_at": self.created_at.isoformat(),
        "user_id": self.user_id,
        "post_id": self.post_id,
        "parent_id": self.parent_id,
        "is_flagged": self.is_flagged,
        "is_approved": self.is_approved,
        "likes": self.likes
    }
