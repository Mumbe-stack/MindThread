from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
)
from flask_mail import Message
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_
import re
import os
import traceback

from models import db, User, TokenBlocklist, Post, Comment


auth_bp = Blueprint("auth", __name__)


UPLOAD_FOLDER = 'uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_email(email):
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
   
    if len(username) < 3 or len(username) > 20:
        return False, "Username must be 3-20 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Valid"

def validate_password(password):
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 100:
        return False, "Password too long (max 100 characters)"
    return True, "Valid"

def admin_required(f):
   
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            if not getattr(user, 'is_admin', False):
                return jsonify({"error": "Admin privileges required"}), 403
            
            if getattr(user, 'is_blocked', False):
                return jsonify({"error": "Account is blocked"}), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Admin check error: {e}")
            return jsonify({"error": "Authorization failed"}), 500
    
    decorated_function.__name__ = f.__name__
    return decorated_function

@auth_bp.route("/register", methods=["POST"])
def register():
    
    try:
        data = request.get_json()
        
       
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
      
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not all([username, email, password]):
            return jsonify({"error": "Username, email, and password are required"}), 400
        
        
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
       
        username_valid, username_message = validate_username(username)
        if not username_valid:
            return jsonify({"error": username_message}), 400
        
      
        password_valid, password_message = validate_password(password)
        if not password_valid:
            return jsonify({"error": password_message}), 400
        
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({"error": "Email already exists"}), 409
        
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            return jsonify({"error": "Username already exists"}), 409
        
       
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            created_at=datetime.now(timezone.utc),
            is_blocked=False,
            is_admin=False,
            is_active=True,
            avatar_url=None  
        )
        
        db.session.add(new_user)
        db.session.commit()
        
       
        access_token = create_access_token(identity=str(new_user.id), fresh=True)
        refresh_token = create_refresh_token(identity=str(new_user.id))
        
      
        try:
            if current_app.extensions.get('mail'):
                msg = Message(
                    "Welcome to MindThread!",
                    recipients=[new_user.email]
                )
                msg.body = f"""Hi {new_user.username},

Welcome to MindThread! We're excited to have you onboard.

Your account has been created successfully. You can now:
- Create and share your thoughts through posts
- Engage with the community through comments
- Like and vote on content you enjoy

Happy posting!

The MindThread Team"""
                current_app.extensions['mail'].send(msg)
                current_app.logger.info(f"Welcome email sent to {new_user.email}")
        except Exception as e:
            current_app.logger.warning(f"Email send failed for {new_user.email}: {e}")
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_admin": new_user.is_admin,
                "is_blocked": new_user.is_blocked,
                "is_active": new_user.is_active,
                "avatar_url": new_user.avatar_url  
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Registration failed. Please try again."}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
  
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
     
        email_or_username = data.get("email", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
      
        login_field = email_or_username if email_or_username else username
        
        if not login_field or not password:
            return jsonify({"error": "Email/username and password are required"}), 400
        
      
        user = None
        if '@' in login_field:
           
            user = User.query.filter_by(email=login_field.lower()).first()
        else:
          
            user = User.query.filter_by(username=login_field).first()
        
        if not user:
            current_app.logger.warning(f"Login failed: No user found for {login_field}")
            return jsonify({"error": "Invalid credentials"}), 401
        
      
        if not check_password_hash(user.password_hash, password):
            current_app.logger.warning(f"Login failed: Password mismatch for {login_field}")
            return jsonify({"error": "Invalid credentials"}), 401
        
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Your account has been blocked. Contact support."}), 403
        
       
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({"error": "Account is inactive. Contact administrator."}), 403
        
      
        access_token = create_access_token(identity=str(user.id), fresh=True)
        refresh_token = create_refresh_token(identity=str(user.id))
        
       
        current_app.logger.info(f"Successful login for user {user.id} ({user.username})")
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": getattr(user, 'is_admin', False),
                "is_blocked": getattr(user, 'is_blocked', False),
                "is_active": getattr(user, 'is_active', True),
                "avatar_url": getattr(user, 'avatar_url', None)  # 🔧 ADDED: Include avatar in login response
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Login failed. Please try again."}), 500

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
  
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account has been blocked"}), 403
        
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": getattr(user, 'is_admin', False),
                "is_blocked": getattr(user, 'is_blocked', False),
                "is_active": getattr(user, 'is_active', True),
                "avatar_url": getattr(user, 'avatar_url', None),  # 🔧 ADDED: Include avatar
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get current user error: {e}")
        return jsonify({"error": "Failed to fetch user data"}), 500

@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_current_user():
  
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account has been blocked"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
       
        if 'username' in data:
            new_username = data['username'].strip()
            username_valid, username_message = validate_username(new_username)
            if not username_valid:
                return jsonify({"error": username_message}), 400
            
          
            existing_user = User.query.filter(
                User.username == new_username,
                User.id != user.id
            ).first()
            if existing_user:
                return jsonify({"error": "Username already exists"}), 409
            
            user.username = new_username
        
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if not validate_email(new_email):
                return jsonify({"error": "Invalid email format"}), 400
            
          
            existing_user = User.query.filter(
                User.email == new_email,
                User.id != user.id
            ).first()
            if existing_user:
                return jsonify({"error": "Email already exists"}), 409
            
            user.email = new_email
        
       
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        current_app.logger.info(f"Profile updated for user {user.id} ({user.username})")
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "is_active": getattr(user, 'is_active', True),
                "avatar_url": getattr(user, 'avatar_url', None)  # 🔧 ADDED: Include avatar
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update profile error: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account is blocked"}), 403
        
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({"error": "Account is inactive"}), 403
        
    
        new_access_token = create_access_token(identity=str(user.id), fresh=False)
        
        return jsonify({
            "success": True,
            "access_token": new_access_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({"error": "Token refresh failed"}), 500

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
   
    try:
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        
       
        blocked_token = TokenBlocklist(jti=jti, created_at=now)
        db.session.add(blocked_token)
        db.session.commit()
        
      
        user_id = get_jwt_identity()
        current_app.logger.info(f"User {user_id} logged out successfully")
        
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
   
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account has been blocked"}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        current_password = data.get("current_password", "").strip()
        new_password = data.get("new_password", "").strip()
        
        if not current_password or not new_password:
            return jsonify({"error": "Current and new password are required"}), 400
        
       
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({"error": "Current password is incorrect"}), 401
        
     
        password_valid, password_message = validate_password(new_password)
        if not password_valid:
            return jsonify({"error": password_message}), 400
        
   
        user.password_hash = generate_password_hash(new_password)
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
     
        current_app.logger.info(f"Password changed for user {user.id} ({user.username})")
        
        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Change password error: {e}")
        return jsonify({"error": "Failed to change password"}), 500

@auth_bp.route("/verify-token", methods=["GET"])
@jwt_required()
def verify_token():
   
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account is blocked"}), 403
        
        return jsonify({
            "success": True,
            "message": "Token is valid",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": getattr(user, 'is_admin', False),
                "is_blocked": getattr(user, 'is_blocked', False),
                "is_active": getattr(user, 'is_active', True),
                "avatar_url": getattr(user, 'avatar_url', None)  
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token verification error: {e}")
        return jsonify({"error": "Token verification failed"}), 500


@auth_bp.route("/upload-avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account is blocked"}), 403

       
        if 'avatar' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
          
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
           
            filename = secure_filename(file.filename)
           
            name, ext = os.path.splitext(filename)
            filename = f"user_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
           
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({"error": "File too large. Maximum size is 5MB"}), 413
            
           
            file.save(file_path)
            
         
            avatar_url = f"/uploads/avatars/{filename}"
            user.avatar_url = avatar_url
            
            if hasattr(user, 'updated_at'):
                user.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()

            current_app.logger.info(f"Avatar uploaded for user {user.id}: {avatar_url}")

            return jsonify({
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": avatar_url,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "avatar_url": avatar_url
                }
            }), 200
        else:
            return jsonify({"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif"}), 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to upload avatar: {e}")
        return jsonify({"error": "Failed to upload avatar"}), 500


@auth_bp.route("/users/me/avatar", methods=["POST"])
@jwt_required()
def upload_avatar_alt():
    
    return upload_avatar()

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
   
    return jsonify({
        "message": "Password reset not implemented yet",
        "status": "coming_soon"
    }), 501

@auth_bp.route("/resend-verification", methods=["POST"])
@jwt_required()
def resend_verification():
   
    return jsonify({
        "message": "Email verification resend not implemented yet",
        "status": "coming_soon"
    }), 501

@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
  
    return jsonify({
        "message": "Email verification not implemented yet",
        "status": "coming_soon"
    }), 501


@auth_bp.route("/test", methods=["GET"])
def test_auth():
    """Test authentication endpoints"""
    return jsonify({
        "success": True,
        "message": "Authentication system is working",
        "endpoints": {
            "register": "POST /api/register",
            "login": "POST /api/login", 
            "logout": "POST /api/logout",
            "refresh": "POST /api/refresh",
            "me": "GET /api/me",
            "change_password": "POST /api/change-password",
            "verify_token": "GET /api/verify-token",
            "upload_avatar": "POST /api/upload-avatar",  
            "upload_avatar_alt": "POST /api/users/me/avatar"  
        },
        "features": [
            "Email/username login support",
            "Automatic token refresh",
            "Token blacklisting on logout",
            "Comprehensive validation",
            "Welcome email notifications",
            "Security logging",
            "Profile management",
            "Avatar upload support"  
        ]
    }), 200


@auth_bp.route("/health", methods=["GET"])
def auth_health():
   
    try:
        
        user_count = User.query.count()
        
        return jsonify({
            "status": "healthy",
            "service": "authentication",
            "database": "connected",
            "user_count": user_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Auth health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "authentication",
            "database": "disconnected",
            "error": str(e)
        }), 503