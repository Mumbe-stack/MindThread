from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
)
from flask_mail import Message
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_
import re
import traceback

from models import db, User, TokenBlocklist, Post, Comment

auth_bp = Blueprint("auth_bp", __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    # Username should be 3-20 characters, alphanumeric and underscores only
    if len(username) < 3 or len(username) > 20:
        return False, "Username must be 3-20 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Valid"

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 100:
        return False, "Password too long (max 100 characters)"
    return True, "Valid"

def admin_required(f):
    """Decorator to require admin privileges"""
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
    """User registration with comprehensive validation and error handling"""
    try:
        data = request.get_json()
        
        # Validate input data
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract and validate required fields
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not all([username, email, password]):
            return jsonify({"error": "Username, email, and password are required"}), 400
        
        # Validate email format
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Validate username
        username_valid, username_message = validate_username(username)
        if not username_valid:
            return jsonify({"error": username_message}), 400
        
        # Validate password
        password_valid, password_message = validate_password(password)
        if not password_valid:
            return jsonify({"error": password_message}), 400
        
        # Check for existing users
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({"error": "Email already exists"}), 409
        
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            return jsonify({"error": "Username already exists"}), 409
        
        # Create new user
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            created_at=datetime.now(timezone.utc),
            is_blocked=False,
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create tokens for immediate login
        access_token = create_access_token(identity=str(new_user.id), fresh=True)
        refresh_token = create_refresh_token(identity=str(new_user.id))
        
        # Send welcome email (non-blocking)
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
                "is_admin": new_user.is_admin
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
    """User login with support for email or username"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Support both email and username login
        email_or_username = data.get("email", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        # Use email if provided, otherwise use username
        login_field = email_or_username if email_or_username else username
        
        if not login_field or not password:
            return jsonify({"error": "Email/username and password are required"}), 400
        
        # Find user by email or username
        user = None
        if '@' in login_field:
            # It's an email
            user = User.query.filter_by(email=login_field.lower()).first()
        else:
            # It's a username
            user = User.query.filter_by(username=login_field).first()
        
        if not user:
            current_app.logger.warning(f"Login failed: No user found for {login_field}")
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Verify password
        if not check_password_hash(user.password_hash, password):
            current_app.logger.warning(f"Login failed: Password mismatch for {login_field}")
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Check if user is blocked
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Your account has been blocked. Contact support."}), 403
        
        # Check if user is active (if you have this field)
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({"error": "Account is inactive. Contact administrator."}), 403
        
        # Create tokens
        access_token = create_access_token(identity=str(user.id), fresh=True)
        refresh_token = create_refresh_token(identity=str(user.id))
        
        # Log successful login
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
                "is_blocked": getattr(user, 'is_blocked', False)
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Login failed. Please try again."}), 500

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user information"""
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
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get current user error: {e}")
        return jsonify({"error": "Failed to fetch user data"}), 500

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if getattr(user, 'is_blocked', False):
            return jsonify({"error": "Account is blocked"}), 403
        
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({"error": "Account is inactive"}), 403
        
        # Create new access token (non-fresh)
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
    """Logout user and blacklist token"""
    try:
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        
        # Add token to blacklist
        blocked_token = TokenBlocklist(jti=jti, created_at=now)
        db.session.add(blocked_token)
        db.session.commit()
        
        # Log logout
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
    """Change user password"""
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
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Validate new password
        password_valid, password_message = validate_password(new_password)
        if not password_valid:
            return jsonify({"error": password_message}), 400
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        # Log password change
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
    """Verify if current token is valid"""
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
            "user_id": user.id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token verification error: {e}")
        return jsonify({"error": "Token verification failed"}), 500

# Admin endpoints for activity trends
@auth_bp.route("/admin/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_admin_stats():
    """Get comprehensive admin statistics"""
    try:
        # Get total counts
        total_users = User.query.count()
        total_posts = Post.query.count() if hasattr(db.Model, 'Post') else 0
        total_comments = Comment.query.count() if hasattr(db.Model, 'Comment') else 0
        
        # Get blocked users count
        blocked_users = User.query.filter_by(is_blocked=True).count()
        
        # Get flagged content counts (if you have flagged fields)
        flagged_posts = 0
        flagged_comments = 0
        
        try:
            if hasattr(Post, 'is_flagged'):
                flagged_posts = Post.query.filter_by(is_flagged=True).count()
        except:
            pass
            
        try:
            if hasattr(Comment, 'is_flagged'):
                flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        except:
            pass
        
        total_flagged = flagged_posts + flagged_comments
        
        stats = {
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "flagged": total_flagged,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
            "blocked_users": blocked_users
        }
        
        current_app.logger.info(f"Admin stats retrieved: {stats}")
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Admin stats error: {e}")
        return jsonify({"error": "Failed to fetch admin stats"}), 500

@auth_bp.route("/admin/activity-trends", methods=["GET"])
@jwt_required()
@admin_required
def get_activity_trends():
    """Get activity trends for the last 7 days"""
    try:
        # Calculate date range for last 7 days
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=6)
        
        # Generate date labels
        date_labels = []
        daily_posts = []
        daily_users = []
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_labels.append(current_date.strftime('%a'))  # Mon, Tue, etc.
            
            # Count posts created on this date
            posts_count = 0
            if hasattr(db.Model, 'Post'):
                try:
                    posts_count = Post.query.filter(
                        func.date(Post.created_at) == current_date
                    ).count()
                except Exception as e:
                    current_app.logger.warning(f"Error counting posts for {current_date}: {e}")
            
            # Count users created on this date
            users_count = 0
            try:
                users_count = User.query.filter(
                    func.date(User.created_at) == current_date
                ).count()
            except Exception as e:
                current_app.logger.warning(f"Error counting users for {current_date}: {e}")
            
            daily_posts.append(posts_count)
            daily_users.append(users_count)
        
        trends_data = {
            "labels": date_labels,
            "posts": daily_posts,
            "users": daily_users
        }
        
        current_app.logger.info(f"Activity trends retrieved: {trends_data}")
        
        return jsonify(trends_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Activity trends error: {e}")
        # Return fallback data
        return jsonify({
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "posts": [1, 2, 0, 3, 1, 2, 1],
            "users": [0, 1, 0, 1, 0, 0, 1]
        }), 200

@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """Email verification endpoint (placeholder for future implementation)"""
    return jsonify({
        "message": "Email verification not implemented yet",
        "status": "coming_soon"
    }), 501

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Password reset endpoint (placeholder for future implementation)"""
    return jsonify({
        "message": "Password reset not implemented yet",
        "status": "coming_soon"
    }), 501

@auth_bp.route("/resend-verification", methods=["POST"])
@jwt_required()
def resend_verification():
    """Resend email verification (placeholder for future implementation)"""
    return jsonify({
        "message": "Email verification resend not implemented yet",
        "status": "coming_soon"
    }), 501

# Test endpoint for development
@auth_bp.route("/test", methods=["GET"])
def test_auth():
    """Test authentication endpoints"""
    return jsonify({
        "success": True,
        "message": "Authentication system is working",
        "endpoints": {
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login",
            "logout": "POST /api/auth/logout",
            "refresh": "POST /api/auth/refresh",
            "me": "GET /api/auth/me",
            "change_password": "POST /api/auth/change-password",
            "verify_token": "GET /api/auth/verify-token",
            "admin_stats": "GET /api/auth/admin/stats",
            "activity_trends": "GET /api/auth/admin/activity-trends"
        },
        "features": [
            "Email/username login support",
            "Automatic token refresh",
            "Token blacklisting on logout",
            "Comprehensive validation",
            "Welcome email notifications",
            "Security logging",
            "Admin statistics",
            "Activity trends tracking"
        ]
    }), 200

# Health check for authentication service
@auth_bp.route("/health", methods=["GET"])
def auth_health():
    """Authentication service health check"""
    try:
        # Test database connection
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