from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timezone, timedelta
from models import db, User, Post, Comment, Vote

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

# Create Blueprint - matches app.py registration pattern
user_bp = Blueprint('users', __name__)

# 🔧 ADDED: Avatar upload configuration
UPLOAD_FOLDER = 'uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 🔧 ADDED: Helper function to get consistent user data dict with avatar support
def get_user_data_dict(user):
    """Helper function to get consistent user data dict with avatar support"""
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_blocked": user.is_blocked,
        "is_active": getattr(user, 'is_active', True),
        "avatar_url": getattr(user, 'avatar_url', None),  # 🔧 ADDED: Always include avatar
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
    }
    
    # Add statistics if available
    try:
        user_data.update({
            "post_count": user.posts.count() if hasattr(user, 'posts') else 0,
            "comment_count": user.comments.count() if hasattr(user, 'comments') else 0,
            "vote_count": user.votes.count() if hasattr(user, 'votes') else 0
        })
    except Exception as e:
        current_app.logger.warning(f"Error adding stats for user {user.id}: {e}")
        user_data.update({
            "post_count": 0,
            "comment_count": 0,
            "vote_count": 0
        })
    
    return user_data

@user_bp.route("/users", methods=["GET"])
@jwt_required()
def fetch_all_users():
    """Get all users (admin only) or search users"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()

        # Build query
        query = User.query
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )

        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())

        # Get users
        users = query.limit(per_page).offset((page - 1) * per_page).all()
        users_data = []
        
        for user in users:
            # 🔧 UPDATED: Use helper function to ensure avatar is included
            user_data = get_user_data_dict(user)
            users_data.append(user_data)

        return jsonify({
            "users": users_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": query.count(),
                "search": search
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch users: {e}")
        return jsonify({"error": "Failed to fetch users"}), 500

@user_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    """Create a new user (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())

        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        data = request.get_json()

        if not data or not all(k in data for k in ("username", "email", "password")):
            return jsonify({"error": "Missing required fields: username, email, password"}), 400

        username = data["username"].strip()
        email = data["email"].strip().lower()
        password = data["password"].strip()

        # Validate input
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # Check for existing users
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 409

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=data.get("is_admin", False),
            is_blocked=data.get("is_blocked", False),
            is_active=data.get("is_active", True),
            avatar_url=None,  # 🔧 ADDED: Initialize avatar as None
            created_at=datetime.now(timezone.utc)
        )

        if hasattr(new_user, 'updated_at'):
            new_user.updated_at = datetime.now(timezone.utc)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user": get_user_data_dict(new_user)  # 🔧 UPDATED: Use helper function
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create user: {e}")
        return jsonify({"error": "Failed to create user"}), 500

@user_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
def fetch_user_by_id(user_id):
    """Get user by ID (own profile or admin) - UPDATED with avatar support"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Check permissions
        if current_user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "Access denied"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # 🔧 UPDATED: Use helper function to ensure avatar is included
        user_data = get_user_data_dict(user)

        # Add user's posts and comments if available
        try:
            if hasattr(user, 'posts'):
                user_data["posts"] = [
                    {
                        "id": p.id,
                        "title": p.title,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    } for p in user.posts.limit(10).all()  # Limit to recent 10
                ]

            if hasattr(user, 'comments'):
                user_data["comments"] = [
                    {
                        "id": c.id,
                        "content": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    } for c in user.comments.limit(10).all()  # Limit to recent 10
                ]
        except Exception as e:
            current_app.logger.warning(f"Error adding user content for user {user_id}: {e}")

        return jsonify(user_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch user {user_id}: {e}")
        return jsonify({"error": "Failed to fetch user"}), 500

@user_bp.route("/users/me", methods=["GET"])
@jwt_required()
def fetch_current_user():
    """Get current user profile - UPDATED with avatar and better stats support"""
    try:
        user = User.query.get(get_jwt_identity())

        if not user:
            return jsonify({"error": "User not found"}), 404

        # 🔧 UPDATED: Enhanced user data with avatar and stats
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_blocked": user.is_blocked,
            "is_active": getattr(user, 'is_active', True),
            "avatar_url": getattr(user, 'avatar_url', None),  # 🔧 ADDED: Include avatar
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
        }

        # Add statistics and recent content
        try:
            user_data["stats"] = {
                "posts_count": user.posts.count() if hasattr(user, 'posts') else 0,
                "comments_count": user.comments.count() if hasattr(user, 'comments') else 0,
                "votes_count": user.votes.count() if hasattr(user, 'votes') else 0
            }

            if hasattr(user, 'posts'):
                user_data["recent_posts"] = [
                    {
                        "id": p.id,
                        "title": p.title,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    } for p in user.posts.order_by(Post.created_at.desc()).limit(5).all()
                ]

            if hasattr(user, 'comments'):
                user_data["recent_comments"] = [
                    {
                        "id": c.id,
                        "content": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    } for c in user.comments.order_by(Comment.created_at.desc()).limit(5).all()
                ]
        except Exception as e:
            current_app.logger.warning(f"Error adding user stats: {e}")
            # Set default stats if there's an error
            user_data["stats"] = {
                "posts_count": 0,
                "comments_count": 0,
                "votes_count": 0
            }

        return jsonify(user_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch current user: {e}")
        return jsonify({"error": "Failed to fetch user data"}), 500

@user_bp.route("/users/me", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_current_user():
    """Update current user profile"""
    try:
        user = User.query.get(get_jwt_identity())
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Fields that can be updated
        updatable_fields = ['username', 'email']
        updated = False

        for field in updatable_fields:
            if field in data:
                new_value = data[field].strip() if isinstance(data[field], str) else data[field]
                
                if field == 'username':
                    if len(new_value) < 3:
                        return jsonify({"error": "Username must be at least 3 characters"}), 400
                    
                    # Check if username already exists (excluding current user)
                    existing_user = User.query.filter(
                        User.username == new_value,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        return jsonify({"error": "Username already exists"}), 409
                
                elif field == 'email':
                    new_value = new_value.lower()
                    # Check if email already exists (excluding current user)
                    existing_user = User.query.filter(
                        User.email == new_value,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        return jsonify({"error": "Email already exists"}), 409
                
                if getattr(user, field) != new_value:
                    setattr(user, field, new_value)
                    updated = True

        # Handle password change separately
        if 'current_password' in data and 'new_password' in data:
            if not check_password_hash(user.password_hash, data['current_password']):
                return jsonify({"error": "Current password is incorrect"}), 400
            
            if len(data['new_password']) < 6:
                return jsonify({"error": "New password must be at least 6 characters"}), 400
            
            user.password_hash = generate_password_hash(data['new_password'])
            updated = True

        if updated:
            if hasattr(user, 'updated_at'):
                user.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Profile updated successfully",
                "user": get_user_data_dict(user)  # 🔧 UPDATED: Use helper function
            }), 200
        else:
            return jsonify({"message": "No changes made"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update user profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

# 🔧 ADDED: Self-deletion endpoint for users to delete their own accounts
@user_bp.route("/users/me", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_current_user():
    """Delete current user's own account"""
    try:
        user = User.query.get(get_jwt_identity())
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Store user info for response
        deleted_user_info = {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }

        # Optional: Clean up avatar file
        if hasattr(user, 'avatar_url') and user.avatar_url:
            try:
                avatar_path = os.path.join(current_app.root_path, user.avatar_url.lstrip('/'))
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)
                    current_app.logger.info(f"Deleted avatar file: {avatar_path}")
            except Exception as e:
                current_app.logger.warning(f"Failed to delete avatar file: {e}")

        # Delete user (cascade should handle related posts, comments, votes)
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Account deleted successfully",
            "deleted_user": deleted_user_info
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete current user: {e}")
        return jsonify({"error": "Failed to delete account"}), 500

@user_bp.route("/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user_by_id(user_id):
    """Update user by ID (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Fields that admin can update
        updatable_fields = ['username', 'email', 'is_admin', 'is_blocked', 'is_active']
        updated = False

        for field in updatable_fields:
            if field in data:
                new_value = data[field]
                
                if field == 'username':
                    new_value = new_value.strip()
                    if len(new_value) < 3:
                        return jsonify({"error": "Username must be at least 3 characters"}), 400
                    
                    # Check if username already exists (excluding current user)
                    existing_user = User.query.filter(
                        User.username == new_value,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        return jsonify({"error": "Username already exists"}), 409
                
                elif field == 'email':
                    new_value = new_value.strip().lower()
                    # Check if email already exists (excluding current user)
                    existing_user = User.query.filter(
                        User.email == new_value,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        return jsonify({"error": "Email already exists"}), 409
                
                if getattr(user, field, None) != new_value:
                    setattr(user, field, new_value)
                    updated = True

        # Handle password reset by admin
        if 'new_password' in data:
            if len(data['new_password']) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400
            
            user.password_hash = generate_password_hash(data['new_password'])
            updated = True

        if updated:
            if hasattr(user, 'updated_at'):
                user.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "User updated successfully",
                "user": get_user_data_dict(user)  # 🔧 UPDATED: Use helper function
            }), 200
        else:
            return jsonify({"message": "No changes made"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update user {user_id}: {e}")
        return jsonify({"error": "Failed to update user"}), 500

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """Delete user by ID (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            return jsonify({"error": "Cannot delete your own account"}), 400

        # Store user info for response
        deleted_user_info = {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }

        # Delete user (this should cascade delete related posts, comments, votes if configured)
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User deleted successfully",
            "deleted_user": deleted_user_info
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete user {user_id}: {e}")
        return jsonify({"error": "Failed to delete user"}), 500

@user_bp.route("/users/<int:user_id>/block", methods=["PATCH"])
@jwt_required()
def block_user(user_id):
    """Block user (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Prevent admin from blocking themselves
        if user.id == current_user.id:
            return jsonify({"error": "Cannot block your own account"}), 400

        # Prevent blocking other admins
        if user.is_admin:
            return jsonify({"error": "Cannot block admin users"}), 400

        user.is_blocked = True
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"User {user.username} has been blocked",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_blocked": user.is_blocked
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to block user {user_id}: {e}")
        return jsonify({"error": "Failed to block user"}), 500

@user_bp.route("/users/<int:user_id>/unblock", methods=["POST"])
@jwt_required()
def unblock_user(user_id):
    """Unblock user (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user.is_blocked = False
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"User {user.username} has been unblocked",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_blocked": user.is_blocked
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to unblock user {user_id}: {e}")
        return jsonify({"error": "Failed to unblock user"}), 500

@user_bp.route("/users/me/avatar", methods=["POST"])
@jwt_required()
@block_check_required
def upload_avatar():
    """Upload user avatar - FULLY IMPLEMENTED"""
    try:
        user = User.query.get(get_jwt_identity())
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if file is in request
        if 'avatar' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            # Create upload directory if it doesn't exist
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Generate secure filename
            filename = secure_filename(file.filename)
            # Add user ID to filename to avoid conflicts
            name, ext = os.path.splitext(filename)
            filename = f"user_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({"error": "File too large. Maximum size is 5MB"}), 413
            
            # Save file
            file.save(file_path)
            
            # Update user avatar path in database
            avatar_url = f"/uploads/avatars/{filename}"
            user.avatar_url = avatar_url
            
            if hasattr(user, 'updated_at'):
                user.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()

            current_app.logger.info(f"Avatar uploaded for user {user.id}: {avatar_url}")

            return jsonify({
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": avatar_url
            }), 200
        else:
            return jsonify({"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif"}), 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to upload avatar: {e}")
        return jsonify({"error": "Failed to upload avatar"}), 500

@user_bp.route("/users/search", methods=["GET"])
@jwt_required()
def search_users():
    """Search users by username or email"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Search query is required"}), 400

        if len(query) < 2:
            return jsonify({"error": "Search query must be at least 2 characters"}), 400

        # Search users
        users = User.query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).filter(User.is_active == True).limit(20).all()

        users_data = []
        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email if current_user.is_admin else None,  # Only show email to admin
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "avatar_url": getattr(user, 'avatar_url', None),  # 🔧 ADDED: Include avatar
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            
            users_data.append(user_data)

        return jsonify({
            "users": users_data,
            "query": query,
            "count": len(users_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to search users: {e}")
        return jsonify({"error": "Failed to search users"}), 500

@user_bp.route("/users/<int:user_id>/stats", methods=["GET"])
@jwt_required()
def get_user_stats_by_id(user_id):
    """Get individual user statistics"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Check permissions - user can view their own stats or admin can view any
        if current_user_id != user_id and (not current_user or not current_user.is_admin):
            return jsonify({"error": "Access denied"}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get user statistics
        try:
            posts_count = user.posts.count() if hasattr(user, 'posts') else 0
            comments_count = user.comments.count() if hasattr(user, 'comments') else 0
            votes_count = user.votes.count() if hasattr(user, 'votes') else 0
        except Exception as e:
            current_app.logger.warning(f"Error counting user stats for user {user_id}: {e}")
            posts_count = comments_count = votes_count = 0

        return jsonify({
            "posts": posts_count,
            "comments": comments_count,
            "votes": votes_count,
            "user_id": user.id,
            "username": user.username
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch user stats for user {user_id}: {e}")
        return jsonify({"error": "Failed to fetch user statistics"}), 500

@user_bp.route("/users/stats", methods=["GET"])
@jwt_required()
def get_global_user_stats():
    """Get global user statistics (admin only)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        from datetime import timedelta
        
        total_users = User.query.count()
        active_users = User.query.filter(User.is_active == True).count()
        blocked_users = User.query.filter(User.is_blocked == True).count()
        admin_users = User.query.filter(User.is_admin == True).count()

        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_registrations = User.query.filter(
            User.created_at >= thirty_days_ago
        ).count()

        return jsonify({
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            "recent_registrations": recent_registrations,
            "inactive_users": total_users - active_users
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch user stats: {e}")
        return jsonify({"error": "Failed to fetch user statistics"}), 500