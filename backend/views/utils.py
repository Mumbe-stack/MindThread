from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from models import User, db
from datetime import datetime, timezone
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)

def block_check_required(fn):
    """
    Decorator to check if user is blocked before allowing access to protected endpoints
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # Allow OPTIONS requests (CORS preflight)
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)
            
            # Get user identity from JWT
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            # Get user from database
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if user is blocked
            if getattr(user, 'is_blocked', False):
                logger.warning(f"Blocked user {user_id} attempted to access {request.endpoint}")
                return jsonify({
                    "error": "Access denied. Your account is blocked.",
                    "blocked": True,
                    "contact_admin": True
                }), 403
            
            # Check if user is active (if you have this field)
            if hasattr(user, 'is_active') and not user.is_active:
                return jsonify({
                    "error": "Account is inactive. Please contact administrator.",
                    "inactive": True
                }), 403
            
            return fn(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in block_check_required: {e}")
            return jsonify({"error": "Authentication error"}), 500
    
    return wrapper

def admin_required(fn):
    """
    Decorator to ensure only admin users can access certain endpoints
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # Allow OPTIONS requests
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)
            
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if user is admin
            if not getattr(user, 'is_admin', False):
                logger.warning(f"Non-admin user {user_id} attempted to access admin endpoint {request.endpoint}")
                return jsonify({"error": "Administrator access required"}), 403
            
            # Also check if admin is blocked
            if getattr(user, 'is_blocked', False):
                return jsonify({
                    "error": "Admin account is blocked. Contact system administrator.",
                    "blocked": True
                }), 403
            
            return fn(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in admin_required: {e}")
            return jsonify({"error": "Authorization error"}), 500
    
    return wrapper

def moderator_required(fn):
    """
    Decorator for moderator privileges (admin or specific moderator role)
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # For now, moderator = admin (can be extended later)
            if not getattr(user, 'is_admin', False):
                return jsonify({"error": "Moderator privileges required"}), 403
            
            if getattr(user, 'is_blocked', False):
                return jsonify({"error": "Account is blocked"}), 403
            
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"Moderator check error: {e}")
            return jsonify({"error": "Authorization failed"}), 500
    
    return wrapper

def rate_limit_decorator(max_requests=100, window_minutes=60):
    """
    Basic rate limiting decorator (you can enhance this with Redis for production)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # Get user ID or IP
                user_id = None
                try:
                    verify_jwt_in_request(optional=True)
                    user_id = get_jwt_identity()
                except:
                    pass
                
                identifier = user_id or request.remote_addr
                
                # Simple in-memory rate limiting (use Redis in production)
                # This is a basic example - implement proper rate limiting for production
                
                return fn(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in rate_limit_decorator: {e}")
                return fn(*args, **kwargs)  # Don't block on rate limit errors
        
        return wrapper
    return decorator

def validate_json_input(required_fields=None, optional_fields=None, max_length=None):
    """
    Decorator to validate JSON input for endpoints
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # Check if request has JSON data
                if not request.is_json:
                    return jsonify({"error": "Request must be JSON"}), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400
                
                # Check required fields
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in data or not data[field]:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return jsonify({
                            "error": f"Missing required fields: {', '.join(missing_fields)}"
                        }), 400
                
                # Validate field lengths
                if max_length:
                    for field, max_len in max_length.items():
                        if field in data and isinstance(data[field], str):
                            if len(data[field]) > max_len:
                                return jsonify({
                                    "error": f"Field '{field}' exceeds maximum length of {max_len}"
                                }), 400
                
                return fn(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in validate_json_input: {e}")
                return jsonify({"error": "Validation error"}), 500
        
        return wrapper
    return decorator

# Data validation helpers
def validate_post_data(data):
    """Validate post creation/update data"""
    errors = []
    
    if not data:
        errors.append("No data provided")
        return errors
    
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    tags = data.get("tags", "").strip()
    
    # Title validation
    if not title:
        errors.append("Title is required")
    elif len(title) < 3:
        errors.append("Title must be at least 3 characters")
    elif len(title) > 200:
        errors.append("Title must be under 200 characters")
    
    # Content validation
    if not content:
        errors.append("Content is required")
    elif len(content) < 10:
        errors.append("Content must be at least 10 characters")
    elif len(content) > 10000:
        errors.append("Content must be under 10,000 characters")
    
    # Tags validation (optional)
    if tags and len(tags) > 255:
        errors.append("Tags must be under 255 characters")
    
    return errors

def validate_comment_data(data):
    """Validate comment creation/update data"""
    errors = []
    
    if not data:
        errors.append("No data provided")
        return errors
    
    content = data.get("content", "").strip()
    post_id = data.get("post_id")
    
    # Content validation
    if not content:
        errors.append("Content is required")
    elif len(content) < 1:
        errors.append("Content cannot be empty")
    elif len(content) > 1000:
        errors.append("Content must be under 1,000 characters")
    
    # Post ID validation (for new comments)
    if post_id is not None:
        try:
            post_id = int(post_id)
            if post_id <= 0:
                errors.append("Invalid post ID")
        except (ValueError, TypeError):
            errors.append("Post ID must be a valid number")
    
    return errors

def validate_user_data(data, is_update=False):
    """Validate user registration/update data"""
    errors = []
    
    if not data:
        errors.append("No data provided")
        return errors
    
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    # Username validation
    if not is_update or username:  # Required for registration, optional for updates
        if not username:
            errors.append("Username is required")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters")
        elif len(username) > 20:
            errors.append("Username must be under 20 characters")
        elif not validate_username(username):
            errors.append("Username can only contain letters, numbers, and underscores")
    
    # Email validation
    if not is_update or email:  # Required for registration, optional for updates
        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Invalid email format")
        elif len(email) > 120:
            errors.append("Email must be under 120 characters")
    
    # Password validation
    if not is_update or password:  # Required for registration, optional for updates
        if not password:
            errors.append("Password is required")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters")
        elif len(password) > 100:
            errors.append("Password must be under 100 characters")
    
    return errors

def sanitize_string(text, max_length=None, allow_html=False):
    """
    Sanitize string input to prevent XSS and other issues
    """
    if not isinstance(text, str):
        return text
    
    # Strip whitespace
    text = text.strip()
    
    # Remove HTML if not allowed
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)
    
    # Remove potentially dangerous content
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Limit length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_email(email):
    """
    Validate email format
    """
    if not email or not isinstance(email, str):
        return False
    
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email.strip()))

def validate_username(username):
    """
    Validate username format
    """
    if not username or not isinstance(username, str):
        return False
    
    # Username should be 3-20 characters, alphanumeric and underscores only
    username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    return bool(username_pattern.match(username.strip()))

def log_user_activity(activity_type, user_id=None, details=None):
    """
    Log user activities for audit purposes
    """
    try:
        if not user_id:
            try:
                verify_jwt_in_request(optional=True)
                user_id = get_jwt_identity()
            except:
                pass
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "activity": activity_type,
            "user_id": user_id,
            "ip_address": get_client_ip(request),
            "user_agent": request.headers.get('User-Agent'),
            "endpoint": request.endpoint,
            "method": request.method,
            "details": details
        }
        
        logger.info(f"User Activity: {log_entry}")
        
        # You can extend this to save to database or external logging service
        
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")

def get_current_user():
    """
    Get current authenticated user object
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
        return None
    except:
        return None

def check_user_permissions(user, required_permissions=None):
    """
    Check if user has required permissions (extend based on your permission system)
    """
    if not user:
        return False
    
    # Check if user is blocked
    if getattr(user, 'is_blocked', False):
        return False
    
    # Check if user is active
    if hasattr(user, 'is_active') and not user.is_active:
        return False
    
    # Check specific permissions if provided
    if required_permissions:
        user_permissions = getattr(user, 'permissions', [])
        for permission in required_permissions:
            if permission not in user_permissions and not getattr(user, 'is_admin', False):
                return False
    
    return True

def handle_database_error(e, operation="database operation"):
    """
    Standardized database error handling
    """
    try:
        db.session.rollback()
    except:
        pass
    
    logger.error(f"Database error during {operation}: {e}")
    
    # Return appropriate error message
    error_str = str(e).lower()
    if "unique constraint" in error_str or "duplicate" in error_str:
        return jsonify({"error": "Duplicate entry - record already exists"}), 409
    elif "foreign key" in error_str:
        return jsonify({"error": "Invalid reference - related record not found"}), 400
    elif "not null" in error_str:
        return jsonify({"error": "Missing required field"}), 400
    else:
        return jsonify({"error": f"Database error during {operation}"}), 500

def success_response(message, data=None, status_code=200):
    """
    Standardized success response format
    """
    response_data = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response_data["data"] = data
    
    return jsonify(response_data), status_code

def error_response(message, error_code=None, status_code=400, details=None):
    """
    Standardized error response format
    """
    response_data = {
        "success": False,
        "error": message
    }
    
    if error_code:
        response_data["error_code"] = error_code
    
    if details:
        response_data["details"] = details
    
    return jsonify(response_data), status_code

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """
    Paginate database queries
    """
    try:
        page = int(request.args.get('page', page))
        per_page = min(int(request.args.get('per_page', per_page)), max_per_page)
        
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            "items": paginated.items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
                "next_page": paginated.next_num if paginated.has_next else None,
                "prev_page": paginated.prev_num if paginated.has_prev else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in pagination: {e}")
        return {
            "items": [],
            "pagination": {
                "page": 1,
                "per_page": per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False,
                "next_page": None,
                "prev_page": None
            }
        }

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for forwarded IP first (common in production with load balancers)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def cors_headers():
    """
    Get CORS headers for responses
    """
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '3600'
    }

# Security utilities
def secure_filename(filename):
    """
    Secure filename for file uploads
    """
    if not filename:
        return "unknown"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Ensure we have something
    if not filename:
        filename = "file"
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename

def is_safe_url(target):
    """
    Check if URL is safe for redirects
    """
    if not target:
        return False
    
    # Basic URL safety check
    return target.startswith(('/', 'http://localhost', 'https://localhost')) or \
           target.startswith(('http://127.0.0.1', 'https://127.0.0.1'))

def check_rate_limit(user_id, action, limit=10, window_minutes=60):
    """Simple in-memory rate limiting (for production, use Redis)"""
    # This is a basic implementation
    # For production, you'd want to use Redis or a proper rate limiting service
    
    import time
    from collections import defaultdict, deque
    
    # In-memory storage (not suitable for production with multiple workers)
    if not hasattr(check_rate_limit, 'requests'):
        check_rate_limit.requests = defaultdict(lambda: defaultdict(deque))
    
    now = time.time()
    window_start = now - (window_minutes * 60)
    
    # Clean old requests
    user_actions = check_rate_limit.requests[user_id][action]
    while user_actions and user_actions[0] < window_start:
        user_actions.popleft()
    
    # Check if limit exceeded
    if len(user_actions) >= limit:
        return False
    
    # Add current request
    user_actions.append(now)
    return True

# Cache utilities (basic implementation)
_cache = {}

def simple_cache(key, value=None, ttl=300):
    """
    Simple in-memory cache (use Redis for production)
    """
    import time
    
    current_time = time.time()
    
    if value is not None:
        # Set cache
        _cache[key] = {
            'value': value,
            'expires': current_time + ttl
        }
        return value
    else:
        # Get cache
        if key in _cache:
            if _cache[key]['expires'] > current_time:
                return _cache[key]['value']
            else:
                del _cache[key]
        return None

def clear_cache(pattern=None):
    """
    Clear cache entries
    """
    global _cache
    if pattern:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]
    else:
        _cache.clear()

# Content moderation helpers
def contains_inappropriate_content(text):
    """Basic content filtering (extend with more sophisticated filtering)"""
    if not text:
        return False
    
    # Basic inappropriate words list (extend as needed)
    inappropriate_patterns = [
        r'\b(spam|phishing|scam)\b',
        r'(http[s]?://[^\s]+){3,}',  # Multiple URLs might be spam
    ]
    
    text_lower = text.lower()
    for pattern in inappropriate_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

def auto_moderate_content(content, content_type="post"):
    """Auto-moderation logic for content"""
    if not content:
        return {"approved": True, "flagged": False, "reason": None}
    
    result = {
        "approved": True,
        "flagged": False,
        "reason": None
    }
    
    # Check for inappropriate content
    if contains_inappropriate_content(content):
        result["approved"] = False
        result["flagged"] = True
        result["reason"] = "Contains potentially inappropriate content"
    
    # Check length limits
    max_length = 10000 if content_type == "post" else 1000
    if len(content) > max_length:
        result["approved"] = False
        result["reason"] = f"Content exceeds maximum length of {max_length} characters"
    
    return result

# Helper function for content statistics
def get_content_stats(user_id=None):
    """Get content statistics for a user or globally"""
    try:
        if user_id:
            # User-specific stats
            user = User.query.get(user_id)
            if not user:
                return None
            
            return {
                "posts_count": user.posts.count(),
                "comments_count": user.comments.count(),
                "approved_posts": user.posts.filter_by(is_approved=True).count(),
                "approved_comments": user.comments.filter_by(is_approved=True).count(),
                "flagged_posts": user.posts.filter_by(is_flagged=True).count(),
                "flagged_comments": user.comments.filter_by(is_flagged=True).count(),
                "total_likes": user.liked_posts.count() + user.liked_comments.count()
            }
        else:
            # Global stats
            from models import Post, Comment
            return {
                "total_posts": Post.query.count(),
                "total_comments": Comment.query.count(),
                "approved_posts": Post.query.filter_by(is_approved=True).count(),
                "approved_comments": Comment.query.filter_by(is_approved=True).count(),
                "flagged_posts": Post.query.filter_by(is_flagged=True).count(),
                "flagged_comments": Comment.query.filter_by(is_flagged=True).count()
            }
    except Exception as e:
        logger.error(f"Error getting content stats: {e}")
        return None
def serialize_comment(comment):
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "user_id": comment.user_id,
        "author": {
            "id": comment.user.id,
            "username": comment.user.username
        } if comment.user else None,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
        "is_approved": comment.is_approved,
        "is_flagged": comment.is_flagged,
        "likes_count": len(comment.likes) if hasattr(comment, 'likes') else 0,
        "vote_score": sum(v.value for v in comment.votes) if hasattr(comment, 'votes') else 0
    }
   
def serialize_post(post, current_user_id=None):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "tags": post.tags,
        "user_id": post.user_id,  
        "author": {
            "id": post.user.id,
            "username": post.user.username,
            "avatar_url": post.user.avatar_url if hasattr(post.user, 'avatar_url') else None
        },
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "is_approved": post.is_approved,
        "is_flagged": post.is_flagged,
        "likes_count": len(post.likes) if hasattr(post, 'likes') else 0,
        "vote_score": sum(v.value for v in post.votes) if hasattr(post, 'votes') else 0,
        "userVote": next((v.value for v in post.votes if v.user_id == current_user_id), None) if current_user_id else None,
        "comments": [serialize_comment(c) for c in post.comments] if hasattr(post, 'comments') else []
    }
