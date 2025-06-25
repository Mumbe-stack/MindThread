from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, Post, User
from .utils import block_check_required  

post_bp = Blueprint('post_bp', __name__, url_prefix="/api/posts")


@post_bp.route("/", methods=["GET"])
@jwt_required(optional=True)
def list_posts():
   
    try:
        posts = Post.query.filter_by(is_approved=True).order_by(Post.created_at.desc()).all()
        return jsonify([{
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "tags": p.tags,
            "user_id": p.user_id,
            "created_at": p.created_at.isoformat()
        } for p in posts]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch posts: {str(e)}"}), 500


@post_bp.route("/", methods=["GET"])
@jwt_required(optional=True)
def get_all_posts():
    try:
        current_user = get_jwt_identity()
        user = User.query.get(current_user) if current_user else None

        if user and user.is_admin:
            posts = Post.query.all()
        else:
            posts = Post.query.filter_by(is_approved=True).all()

        return jsonify([{
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat(),
            "is_approved": post.is_approved,
            "is_flagged": post.is_flagged
        } for post in posts]), 200

    except Exception as e:
        print("Error in get_all_posts:", e)
        return jsonify({"error": "Failed to fetch posts"}), 500


@post_bp.route("/", methods=["POST"])
@jwt_required()
@block_check_required 
def create_post():
   
    try:
        data = request.get_json()
        user_id = get_jwt_identity()

        if not data or not all(k in data for k in ("title", "content")):
            return jsonify({"error": "Missing required fields: title and content"}), 400

       
        title = data["title"].strip()
        content = data["content"].strip()

        if not title or not content:
            return jsonify({"error": "Title and content cannot be empty"}), 400

        if len(title) > 200:
            return jsonify({"error": "Title must be less than 200 characters"}), 400

        
        existing = Post.query.filter_by(user_id=user_id, title=title).first()
        if existing:
            return jsonify({"error": "You already have a post with this title"}), 409

        new_post = Post(
            title=title,
            content=content,
            tags=data.get("tags", "").strip() if data.get("tags") else None,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_post)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post created successfully",
            "post_id": new_post.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create post: {str(e)}"}), 500


@post_bp.route("/<int:id>", methods=["PATCH"])  
@block_check_required 
def update_post(id):
   
    try:
        post = Post.query.get_or_404(id)
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)

        
        if post.user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "You can only edit your own posts"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        #
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            if len(title) > 200:
                return jsonify({"error": "Title must be less than 200 characters"}), 400
            
           
            existing = Post.query.filter_by(user_id=post.user_id, title=title).first()
            if existing and existing.id != post.id:
                return jsonify({"error": "You already have a post with this title"}), 409
            
            post.title = title

        if "content" in data:
            content = data["content"].strip()
            if not content:
                return jsonify({"error": "Content cannot be empty"}), 400
            post.content = content

        if "tags" in data:
            post.tags = data["tags"].strip() if data["tags"] else None

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post updated successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "tags": post.tags
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update post: {str(e)}"}), 500


@post_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
@block_check_required  
def delete_post(id):
   
    try:
        post = Post.query.get_or_404(id)
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)

       
        if post.user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "You can only delete your own posts"}), 403

        title = post.title 
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Post '{title}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete post: {str(e)}"}), 500


@post_bp.route("/<int:id>/like", methods=["PATCH"])
@jwt_required()
@block_check_required  
def like_post(id):
   
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        if post in user.liked_posts:
            return jsonify({"error": "You have already liked this post"}), 400

        user.liked_posts.append(post)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Post '{post.title}' liked",
            "liked_by": {"id": user.id, "username": user.username}
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to like post: {str(e)}"}), 500


@post_bp.route("/<int:id>/unlike", methods=["PATCH"])
@jwt_required()
@block_check_required 
def unlike_post(id):
   
    try:
        post = Post.query.get_or_404(id)
        user = User.query.get(get_jwt_identity())

        if post not in user.liked_posts:
            return jsonify({"error": "You haven't liked this post yet"}), 400

        user.liked_posts.remove(post)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Post '{post.title}' unliked",
            "unliked_by": {"id": user.id, "username": user.username}
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to unlike post: {str(e)}"}), 500


@post_bp.route("/<int:id>/approve", methods=["PATCH"])
@jwt_required()
def approve_post(id):
    
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        post = Post.query.get_or_404(id)
        data = request.get_json()

        if "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        post.is_approved = bool(data["is_approved"])
        post.is_flagged = False  
        db.session.commit()

        status = "approved" if post.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Post '{post.title}' {status}"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process post: {str(e)}"}), 500


@post_bp.route("/<int:id>/flag", methods=["PATCH"])
@jwt_required()
def flag_post(id):
   
    try:
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        post = Post.query.get_or_404(id)
        post.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Post '{post.title}' flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag post: {str(e)}"}), 500


def to_dict(self):
   
    return {
        "id": self.id,
        "title": self.title,
        "content": self.content,
        "tags": self.tags,
        "created_at": self.created_at.isoformat(),
        "user_id": self.user_id,
        "is_approved": self.is_approved,
        "is_flagged": self.is_flagged
    }