from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
from models import db, User, Post, Comment, Vote
from flask import current_app

from .utils import block_check_required

user_bp = Blueprint('user_bp', __name__, url_prefix="/api/users")


UPLOAD_FOLDER = 'uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@user_bp.route("", methods=["GET"])  # Change from "/" to ""
@jwt_required()
def fetch_all_users():
    """Get all users - Admin Dashboard needs this"""
    current_user = User.query.get(get_jwt_identity())
    
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        users = User.query.all()
        return jsonify([{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_blocked": u.is_blocked,
            "created_at": u.created_at.isoformat(),
            "post_count": len(u.posts),
            "comment_count": len(u.comments)
        } for u in users]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500


@user_bp.route("/", methods=["POST"])
@jwt_required()
def create_user():
    
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin privileges required"}), 403

    data = request.get_json()

    if not data or not all(k in data for k in ("username", "email", "password")):
        return jsonify({"error": "Missing required fields: username, email, password"}), 400

   
    if len(data["username"]) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    
    if len(data["password"]) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

   
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409
    
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409

    try:
        new_user = User(
            username=data["username"].strip(),
            email=data["email"].strip().lower(),
            password_hash=generate_password_hash(data["password"]),
            is_admin=data.get("is_admin", False)
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_admin": new_user.is_admin
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500


@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def fetch_user_by_id(user_id):
    
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
   
    if current_user_id != user_id and (not current_user or not current_user.is_admin):
        return jsonify({"error": "Access denied"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat(),
        "posts": [{"id": p.id, "title": p.title, "created_at": p.created_at.isoformat()} for p in user.posts],
        "comments": [{"id": c.id, "content": c.content[:100], "created_at": c.created_at.isoformat()} for c in user.comments]
    }), 200


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def fetch_current_user():
   
    user = User.query.get(get_jwt_identity())

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat(),
        "posts": [{"id": p.id, "title": p.title, "created_at": p.created_at.isoformat()} for p in user.posts],
        "comments": [{"id": c.id, "content": c.content[:100], "created_at": c.created_at.isoformat()} for c in user.comments]
    }), 200


@user_bp.route("/me", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_current_user():
   
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

       
        username = user.username

       
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Account '{username}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete account: {str(e)}"}), 500


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user_by_id(user_id):
   
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User '{username}' deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


@user_bp.route("/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
   
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    
    if current_user_id != user_id and (not current_user or not current_user.is_admin):
        return jsonify({"error": "Access denied"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
      
        if "username" in data and data["username"].strip():
            
            existing = User.query.filter_by(username=data["username"]).first()
            if existing and existing.id != user_id:
                return jsonify({"error": "Username already exists"}), 409
            user.username = data["username"].strip()

        if "email" in data and data["email"].strip():
            
            existing = User.query.filter_by(email=data["email"]).first()
            if existing and existing.id != user_id:
                return jsonify({"error": "Email already exists"}), 409
            user.email = data["email"].strip().lower()

       
        if "is_admin" in data and current_user and current_user.is_admin:
            user.is_admin = bool(data["is_admin"])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500


@user_bp.route("/<int:user_id>/block", methods=["PATCH"])
@jwt_required()
def toggle_user_block(user_id):
   
    current_user = User.query.get(get_jwt_identity())

    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        user.is_blocked = not user.is_blocked
        db.session.commit()

        status = "blocked" if user.is_blocked else "unblocked"
        return jsonify({
            "success": True,
            "message": f"User '{user.username}' has been {status}",
            "is_blocked": user.is_blocked
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update user status: {str(e)}"}), 500


@user_bp.route("/upload-avatar", methods=["POST"])
@jwt_required()
@block_check_required
def upload_avatar():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

       
        if 'avatar' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF"}), 400

        
        if len(file.read()) > MAX_FILE_SIZE:
            return jsonify({"error": "File too large. Maximum size: 5MB"}), 400
        
        file.seek(0)  

        
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        
        filename = secure_filename(f"user_{user_id}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

       
        file.save(filepath)


        return jsonify({
            "success": True,
            "message": "Avatar uploaded successfully",
            "filename": filename
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to upload avatar: {str(e)}"}), 500
    

@user_bp.route("/<int:user_id>/stats/", methods=["GET"])
@jwt_required()
def get_user_stats(user_id):
    try:
        user = User.query.get_or_404(user_id)

        post_count = Post.query.filter_by(user_id=user.id).count()
        comment_count = Comment.query.filter_by(user_id=user.id).count()
        vote_count = Vote.query.filter_by(user_id=user.id).count()

        return jsonify({
            "posts": post_count,
            "comments": comment_count,
            "votes": vote_count
        }), 200

    except Exception as e:
        current_app.logger.exception("Failed to fetch user stats")
        return jsonify({"error": "Failed to fetch user stats"}), 500

@user_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_user(id):
    admin = User.query.get(get_jwt_identity())
    if not admin or not admin.is_admin:
        return jsonify({"error": "Admin only"}), 403

    target = User.query.get_or_404(id)
    db.session.delete(target)
    db.session.commit()
    return jsonify({"message": f"User {id} deleted"}), 200