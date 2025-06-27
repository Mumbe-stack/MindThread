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


@comment_bp.route("", methods=["GET"])
@jwt_required()
def get_all_comments():
    """Get all comments - Admin Dashboard needs this"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
       
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
            
        comments = Comment.query.order_by(Comment.created_at.desc()).all()
        return jsonify([{
            "id": c.id,
            "content": c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
            "is_approved": getattr(c, 'is_approved', True),  
            "is_flagged": getattr(c, 'is_flagged', False)  
        } for c in comments]), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500

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
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post
from datetime import datetime, timezone
from .utils import block_check_required 

comment_bp = Blueprint('comment_bp', __name__)


@comment_bp.route("/", methods=["GET"])
def list_comments():
    """Get comments for a post - no authentication required to view"""
    try:
        post_id = request.args.get("post_id")
        user_id = request.args.get("user_id")

        query = Comment.query
        if post_id:
            query = query.filter_by(post_id=post_id)
        if user_id:
            query = query.filter_by(user_id=user_id)

        comments = query.order_by(Comment.created_at.asc()).all()

        # Check if user is authenticated (optional for viewing)
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except:
            pass  # User not authenticated, that's fine for viewing

        comments_data = []
        for c in comments:
            comment_data = {
                "id": c.id,
                "content": c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat(),
                "likes": len(c.liked_by_users) if hasattr(c, 'liked_by_users') and c.liked_by_users else 0,
                "liked_by": [user.id for user in c.liked_by_users] if hasattr(c, 'liked_by_users') and c.liked_by_users else []
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200

    except Exception as e:
        print(f"Error fetching comments: {e}")
        return jsonify({"error": "Failed to fetch comments"}), 500


@comment_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required
def create_comment():
    """Create a new comment - authentication required"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()

        if not data.get("content") or not data.get("post_id"):
            return jsonify({"error": "Missing fields: content and post_id are required"}), 400

        # Validate content
        content = data["content"].strip()
        if len(content) < 1:
            return jsonify({"error": "Comment content cannot be empty"}), 400

        if len(content) > 1000:
            return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400

        post = Post.query.get(data["post_id"])
        if not post:
            return jsonify({"error": f"Post with ID {data['post_id']} does not exist"}), 404

        parent_id = data.get("parent_id")
        if parent_id:
            parent_comment = Comment.query.get(parent_id)
            if not parent_comment:
                return jsonify({"error": f"Parent comment with ID {parent_id} does not exist"}), 404

        comment = Comment(
            content=content,
            post_id=data["post_id"],
            user_id=user_id,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc)
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment created successfully",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "parent_id": comment.parent_id,
                "created_at": comment.created_at.isoformat(),
                "likes": 0,
                "liked_by": []
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating comment: {e}")
        return jsonify({"error": "Failed to create comment"}), 500


@comment_bp.route("", methods=["GET"])
@jwt_required()
def get_all_comments():
    """Get all comments - Admin Dashboard needs this"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
            
        comments = Comment.query.order_by(Comment.created_at.desc()).all()
        return jsonify([{
            "id": c.id,
            "content": c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
            "is_approved": getattr(c, 'is_approved', True),  
            "is_flagged": getattr(c, 'is_flagged', False),
            "likes": len(c.liked_by_users) if hasattr(c, 'liked_by_users') and c.liked_by_users else 0
        } for c in comments]), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch comments: {str(e)}"}), 500


@comment_bp.route("/<int:comment_id>/like", methods=["POST"])
@jwt_required()
def like_comment(comment_id):
    """Toggle like on a comment - authentication required"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        comment = Comment.query.get_or_404(comment_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user already liked this comment
        if hasattr(comment, 'liked_by_users') and user in comment.liked_by_users:
            comment.liked_by_users.remove(user)
            message = "Comment unliked"
        else:
            if not hasattr(comment, 'liked_by_users'):
                # Initialize the relationship if it doesn't exist
                comment.liked_by_users = []
            comment.liked_by_users.append(user)
            message = "Comment liked"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "likes": len(comment.liked_by_users) if hasattr(comment, 'liked_by_users') else 0,
            "liked_by": [u.id for u in comment.liked_by_users] if hasattr(comment, 'liked_by_users') else []
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error toggling comment like: {e}")
        return jsonify({"error": "Failed to toggle like"}), 500


@comment_bp.route("/<int:comment_id>/like/", methods=["POST", "OPTIONS"])
def like_comment_with_slash(comment_id):
    """Handle the route with trailing slash for compatibility"""
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200
    
    # Redirect to the main like function
    return like_comment(comment_id)


@comment_bp.route("/<int:id>/unlike", methods=["PATCH"])
@jwt_required()
@block_check_required
def unlike_comment(id):
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(id)
    user = User.query.get(user_id)

    if not hasattr(comment, 'liked_by_users') or user not in comment.liked_by_users:
        return jsonify({"error": "You haven't liked this comment yet"}), 400

    comment.liked_by_users.remove(user)
    db.session.commit()

    return jsonify({
        "message": f"Comment ID {id} unliked",
        "likes": len(comment.liked_by_users) if hasattr(comment, 'liked_by_users') else 0,
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
    """Get replies to a comment - no authentication required"""
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
            "created_at": reply.created_at.isoformat(),
            "likes": len(reply.liked_by_users) if hasattr(reply, 'liked_by_users') and reply.liked_by_users else 0,
            "liked_by": [user.id for user in reply.liked_by_users] if hasattr(reply, 'liked_by_users') and reply.liked_by_users else []
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
        "is_flagged": getattr(self, 'is_flagged', False),
        "is_approved": getattr(self, 'is_approved', True),
        "likes": len(self.liked_by_users) if hasattr(self, 'liked_by_users') and self.liked_by_users else 0,
        "liked_by": [user.id for user in self.liked_by_users] if hasattr(self, 'liked_by_users') and self.liked_by_users else []
    }

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
