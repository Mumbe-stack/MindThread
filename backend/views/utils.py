from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from models import User, db
from datetime import datetime, timezone
import re
import logging
import time
from collections import defaultdict, deque

# Set up logging
logger = logging.getLogger(__name__)

# Global cache and rate limiting storage
_cache = {}
_rate_limit_storage = defaultdict(lambda: defaultdict(deque))

# ===== AUTHENTICATION & AUTHORIZATION DECORATORS =====

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
    Basic rate limiting decorator
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
                except Exception:
                    pass
                
                identifier = user_id or get_client_ip(request)
                action = f"{request.endpoint}:{request.method}"
                
                # Check rate limit
                if not check_rate_limit(identifier, action, max_requests, window_minutes):
                    return jsonify({
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": window_minutes * 60
                    }), 429
                
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

# ===== DATA VALIDATION FUNCTIONS =====

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

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email.strip()))

def validate_username(username):
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False
    
    # Username should be 3-20 characters, alphanumeric and underscores only
    username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    return bool(username_pattern.match(username.strip()))

# ===== SANITIZATION FUNCTIONS =====

def sanitize_string(text, max_length=None, allow_html=False):
    """Sanitize string input to prevent XSS and other issues"""
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

def secure_filename(filename):
    """Secure filename for file uploads"""
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

# ===== RESPONSE HELPERS =====

def success_response(message, data=None, status_code=200):
    """Standardized success response format"""
    response_data = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response_data["data"] = data
    
    return jsonify(response_data), status_code

def error_response(message, error_code=None, status_code=400, details=None):
    """Standardized error response format"""
    response_data = {
        "success": False,
        "error": message
    }
    
    if error_code:
        response_data["error_code"] = error_code
    
    if details:
        response_data["details"] = details
    
    return jsonify(response_data), status_code

def handle_database_error(e, operation="database operation"):
    """Standardized database error handling"""
    try:
        db.session.rollback()
    except Exception:
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

# ===== PAGINATION HELPERS =====

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Paginate database queries"""
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

# ===== USER & SECURITY UTILITIES =====

def log_user_activity(activity_type, user_id=None, details=None):
    """Log user activities for audit purposes"""
    try:
        if not user_id:
            try:
                verify_jwt_in_request(optional=True)
                user_id = get_jwt_identity()
            except Exception:
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
        
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")

def get_current_user():
    """Get current authenticated user object"""
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
        return None
    except Exception:
        return None

def check_user_permissions(user, required_permissions=None):
    """Check if user has required permissions"""
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

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for forwarded IP first (common in production with load balancers)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def is_safe_url(target):
    """Check if URL is safe for redirects"""
    if not target:
        return False
    
    # Basic URL safety check
    return target.startswith(('/', 'http://localhost', 'https://localhost')) or \
           target.startswith(('http://127.0.0.1', 'https://127.0.0.1'))

# ===== RATE LIMITING =====

def check_rate_limit(user_id, action, limit=10, window_minutes=60):
    """Simple in-memory rate limiting"""
    global _rate_limit_storage
    
    now = time.time()
    window_start = now - (window_minutes * 60)
    
    # Clean old requests
    user_actions = _rate_limit_storage[user_id][action]
    while user_actions and user_actions[0] < window_start:
        user_actions.popleft()
    
    # Check if limit exceeded
    if len(user_actions) >= limit:
        return False
    
    # Add current request
    user_actions.append(now)
    return True

# ===== CACHING =====

def simple_cache(key, value=None, ttl=300):
    """Simple in-memory cache (use Redis for production)"""
    global _cache
    
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
    """Clear cache entries"""
    global _cache
    if pattern:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]
    else:
        _cache.clear()

# ===== CONTENT MODERATION =====

def contains_inappropriate_content(text):
    """Basic content filtering"""
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

# ===== STATISTICS & ANALYTICS =====

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
                "total_likes": getattr(user, 'liked_posts', []) and len(user.liked_posts) + 
                             getattr(user, 'liked_comments', []) and len(user.liked_comments) or 0
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

# ===== CORS UTILITIES =====

def cors_headers():
    """Get CORS headers for responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '3600'
    }

# ===== FILE HANDLING =====

def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_size(file):
    """Get file size in bytes"""
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Seek back to start
    return size

# ===== API ENDPOINT HELPERS =====

def extract_sort_params(default_sort='created_at', default_order='desc'):
    """Extract sort parameters from request"""
    sort_by = request.args.get('sort', default_sort)
    order = request.args.get('order', default_order).lower()
    
    # Validate order
    if order not in ['asc', 'desc']:
        order = default_order
    
    return sort_by, order

def extract_filter_params():
    """Extract common filter parameters from request"""
    return {
        'search': request.args.get('search', '').strip(),
        'status': request.args.get('status'),
        'user_id': request.args.get('user_id', type=int),
        'category': request.args.get('category'),
        'tags': request.args.get('tags'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to')
    }

# ===== DATETIME UTILITIES =====

def format_datetime(dt, format_type='iso'):
    """Format datetime object"""
    if not dt:
        return None
    
    if format_type == 'iso':
        return dt.isoformat()
    elif format_type == 'readable':
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    elif format_type == 'date_only':
        return dt.strftime('%Y-%m-%d')
    else:
        return str(dt)

def parse_datetime(date_string):
    """Parse datetime string"""
    if not date_string:
        return None
    
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except ValueError:
        try:
            # Try common format
            return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try date only
                return datetime.strptime(date_string, '%Y-%m-%d')
            except ValueError:
                return None

# ===== VALIDATION DECORATORS =====

def require_fields(*fields):
    """Decorator to require specific fields in request JSON"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return error_response("Request must be JSON", status_code=400)
            
            data = request.get_json()
            if not data:
                return error_response("No JSON data provided", status_code=400)
            
            missing = [field for field in fields if field not in data or not data[field]]
            if missing:
                return error_response(f"Missing required fields: {', '.join(missing)}", status_code=400)
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def validate_content_type(*content_types):
    """Decorator to validate request content type"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.content_type not in content_types:
                return error_response(
                    f"Invalid content type. Expected: {', '.join(content_types)}", 
                    status_code=415
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ===== HELPER FUNCTIONS FOR API CONSISTENCY =====

def standardize_user_response(user):
    """Standardize user object for API responses"""
    if not user:
        return None
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email if hasattr(user, 'email') else None,
        "is_admin": getattr(user, 'is_admin', False),
        "is_blocked": getattr(user, 'is_blocked', False),
        "is_active": getattr(user, 'is_active', True),
        "created_at": format_datetime(user.created_at),
        "updated_at": format_datetime(getattr(user, 'updated_at', None))
    }

def standardize_post_response(post, include_author=True, include_stats=True):
    """Standardize post object for API responses"""
    if not post:
        return None
    
    response = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "is_approved": getattr(post, 'is_approved', True),
        "is_flagged": getattr(post, 'is_flagged', False),
        "created_at": format_datetime(post.created_at),
        "updated_at": format_datetime(getattr(post, 'updated_at', None))
    }
    
    if include_author:
        author = User.query.get(post.user_id) if hasattr(post, 'user_id') else None
        response["author"] = standardize_user_response(author) if author else None
    
    if include_stats:
        response["stats"] = {
            "likes_count": getattr(post, 'likes_count', 0),
            "comments_count": getattr(post, 'comments_count', 0),
            "votes_score": getattr(post, 'votes_score', 0)
        }
    
    return response

def standardize_comment_response(comment, include_author=True):
    """Standardize comment object for API responses"""
    if not comment:
        return None
    
    response = {
        "id": comment.id,
        "content": comment.content,
        "post_id": getattr(comment, 'post_id', None),
        "is_approved": getattr(comment, 'is_approved', True),
        "is_flagged": getattr(comment, 'is_flagged', False),
        "created_at": format_datetime(comment.created_at),
        "updated_at": format_datetime(getattr(comment, 'updated_at', None))
    }
    
    if include_author:
        author = User.query.get(comment.user_id) if hasattr(comment, 'user_id') else None
        response["author"] = standardize_user_response(author) if author else None
    
    return response

# ===== ADVANCED UTILITIES =====

def bulk_operation(model_class, operation, ids, **kwargs):
    """Perform bulk operations on multiple records"""
    try:
        if not ids or not isinstance(ids, list):
            return {"success": False, "error": "Invalid IDs provided"}
        
        query = model_class.query.filter(model_class.id.in_(ids))
        
        if operation == 'delete':
            count = query.count()
            query.delete(synchronize_session=False)
            db.session.commit()
            return {"success": True, "affected_count": count, "operation": "delete"}
        
        elif operation == 'update':
            update_data = kwargs.get('update_data', {})
            if not update_data:
                return {"success": False, "error": "No update data provided"}
            
            count = query.update(update_data, synchronize_session=False)
            db.session.commit()
            return {"success": True, "affected_count": count, "operation": "update"}
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk operation error: {e}")
        return {"success": False, "error": str(e)}

def search_content(query_text, content_types=None, filters=None):
    """Advanced content search across posts and comments"""
    try:
        from models import Post, Comment
        from sqlalchemy import or_, and_
        
        results = {"posts": [], "comments": []}
        
        if not query_text or len(query_text.strip()) < 2:
            return results
        
        search_term = f"%{query_text.strip()}%"
        
        # Search posts
        if not content_types or 'posts' in content_types:
            post_query = Post.query.filter(
                or_(
                    Post.title.ilike(search_term),
                    Post.content.ilike(search_term)
                )
            )
            
            # Apply filters
            if filters:
                if filters.get('approved_only'):
                    post_query = post_query.filter(Post.is_approved == True)
                if filters.get('exclude_flagged'):
                    post_query = post_query.filter(Post.is_flagged == False)
                if filters.get('user_id'):
                    post_query = post_query.filter(Post.user_id == filters['user_id'])
            
            posts = post_query.limit(50).all()
            results["posts"] = [standardize_post_response(post) for post in posts]
        
        # Search comments
        if not content_types or 'comments' in content_types:
            comment_query = Comment.query.filter(
                Comment.content.ilike(search_term)
            )
            
            # Apply filters
            if filters:
                if filters.get('approved_only'):
                    comment_query = comment_query.filter(Comment.is_approved == True)
                if filters.get('exclude_flagged'):
                    comment_query = comment_query.filter(Comment.is_flagged == False)
                if filters.get('user_id'):
                    comment_query = comment_query.filter(Comment.user_id == filters['user_id'])
            
            comments = comment_query.limit(50).all()
            results["comments"] = [standardize_comment_response(comment) for comment in comments]
        
        return results
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"posts": [], "comments": [], "error": str(e)}

def generate_analytics_report(user_id=None, date_range=None):
    """Generate comprehensive analytics report"""
    try:
        from models import Post, Comment, User
        from sqlalchemy import func, desc, and_
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date_range": date_range,
            "summary": {},
            "top_content": {},
            "user_activity": {},
            "trends": {}
        }
        
        # Base queries
        base_filters = []
        if date_range:
            if date_range.get('start'):
                start_date = parse_datetime(date_range['start'])
                if start_date:
                    base_filters.append(Post.created_at >= start_date)
            if date_range.get('end'):
                end_date = parse_datetime(date_range['end'])
                if end_date:
                    base_filters.append(Post.created_at <= end_date)
        
        if user_id:
            base_filters.append(Post.user_id == user_id)
        
        # Summary statistics
        post_query = Post.query
        comment_query = Comment.query
        
        if base_filters:
            post_query = post_query.filter(and_(*base_filters))
            comment_filters = [f for f in base_filters if hasattr(Comment, str(f.left).split('.')[1])]
            if comment_filters:
                comment_query = comment_query.filter(and_(*comment_filters))
        
        report["summary"] = {
            "total_posts": post_query.count(),
            "approved_posts": post_query.filter(Post.is_approved == True).count(),
            "flagged_posts": post_query.filter(Post.is_flagged == True).count(),
            "total_comments": comment_query.count(),
            "approved_comments": comment_query.filter(Comment.is_approved == True).count(),
            "flagged_comments": comment_query.filter(Comment.is_flagged == True).count()
        }
        
        # Top content (most liked posts)
        top_posts = post_query.filter(Post.is_approved == True).order_by(
            desc(func.coalesce(getattr(Post, 'likes_count', 0), 0))
        ).limit(10).all()
        
        report["top_content"]["posts"] = [
            standardize_post_response(post, include_stats=True) for post in top_posts
        ]
        
        # User activity (if not user-specific report)
        if not user_id:
            active_users = db.session.query(
                User.id,
                User.username,
                func.count(Post.id).label('post_count')
            ).outerjoin(Post).group_by(User.id).order_by(
                desc(func.count(Post.id))
            ).limit(10).all()
            
            report["user_activity"]["most_active"] = [
                {
                    "user_id": user.id,
                    "username": user.username,
                    "posts": user.post_count,
                    "total_activity": user.post_count
                }
                for user in active_users
            ]
        
        return report
    
    except Exception as e:
        logger.error(f"Analytics report generation error: {e}")
        return {"error": str(e)}

def export_data(data_type, format_type='json', filters=None):
    """Export data in various formats"""
    try:
        from models import Post, Comment, User
        import json
        import csv
        from io import StringIO
        
        if data_type == 'posts':
            query = Post.query
            if filters:
                if filters.get('approved_only'):
                    query = query.filter(Post.is_approved == True)
                if filters.get('user_id'):
                    query = query.filter(Post.user_id == filters['user_id'])
            
            posts = query.all()
            data = [standardize_post_response(post) for post in posts]
        
        elif data_type == 'comments':
            query = Comment.query
            if filters:
                if filters.get('approved_only'):
                    query = query.filter(Comment.is_approved == True)
                if filters.get('post_id'):
                    query = query.filter(Comment.post_id == filters['post_id'])
            
            comments = query.all()
            data = [standardize_comment_response(comment) for comment in comments]
        
        elif data_type == 'users':
            users = User.query.all()
            data = [standardize_user_response(user) for user in users]
        
        else:
            return {"success": False, "error": f"Unknown data type: {data_type}"}
        
        if format_type == 'json':
            return {
                "success": True,
                "data": json.dumps(data, indent=2),
                "content_type": "application/json",
                "filename": f"{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        
        elif format_type == 'csv':
            if not data:
                return {"success": False, "error": "No data to export"}
            
            output = StringIO()
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data:
                    # Flatten nested objects for CSV
                    flat_row = {}
                    for key, value in row.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                flat_row[f"{key}_{sub_key}"] = sub_value
                        else:
                            flat_row[key] = value
                    writer.writerow(flat_row)
            
            return {
                "success": True,
                "data": output.getvalue(),
                "content_type": "text/csv",
                "filename": f"{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        
        else:
            return {"success": False, "error": f"Unknown format: {format_type}"}
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        return {"success": False, "error": str(e)}

def health_check():
    """Comprehensive system health check"""
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    try:
        # Database connectivity
        try:
            db.session.execute('SELECT 1')
            health_status["checks"]["database"] = {"status": "healthy", "message": "Connected"}
        except Exception as e:
            health_status["checks"]["database"] = {"status": "unhealthy", "message": str(e)}
            health_status["status"] = "unhealthy"
        
        # Cache status
        health_status["checks"]["cache"] = {"status": "healthy", "message": "In-memory cache operational"}
        
        # File system access
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=True) as f:
                f.write(b"test")
                f.flush()
            health_status["checks"]["filesystem"] = {"status": "healthy", "message": "Read/write access"}
        except Exception as e:
            health_status["checks"]["filesystem"] = {"status": "unhealthy", "message": str(e)}
        
        # Memory usage
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            health_status["checks"]["memory"] = {
                "status": "healthy" if memory_percent < 90 else "warning",
                "usage_percent": memory_percent
            }
        except ImportError:
            health_status["checks"]["memory"] = {"status": "unknown", "message": "psutil not available"}
        except Exception as e:
            health_status["checks"]["memory"] = {"status": "error", "message": str(e)}
        
        # Rate limiting storage
        global _rate_limit_storage
        health_status["checks"]["rate_limiting"] = {
            "status": "healthy",
            "active_limits": len(_rate_limit_storage)
        }
        
        # Cache storage
        global _cache
        health_status["checks"]["cache_storage"] = {
            "status": "healthy",
            "cached_items": len(_cache)
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        health_status["status"] = "error"
        health_status["error"] = str(e)
    
    return health_status

def cleanup_expired_data():
    """Clean up expired data (cache, rate limits, etc.)"""
    try:
        global _cache, _rate_limit_storage
        
        current_time = time.time()
        cleanup_stats = {
            "cache_cleaned": 0,
            "rate_limits_cleaned": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Clean expired cache entries
        expired_cache_keys = []
        for key, data in _cache.items():
            if data['expires'] <= current_time:
                expired_cache_keys.append(key)
        
        for key in expired_cache_keys:
            del _cache[key]
            cleanup_stats["cache_cleaned"] += 1
        
        # Clean old rate limit entries (older than 24 hours)
        cutoff_time = current_time - (24 * 60 * 60)
        users_to_clean = []
        
        for user_id, actions in _rate_limit_storage.items():
            actions_to_clean = []
            for action, timestamps in actions.items():
                # Remove old timestamps
                while timestamps and timestamps[0] < cutoff_time:
                    timestamps.popleft()
                    cleanup_stats["rate_limits_cleaned"] += 1
                
                # Mark empty action queues for removal
                if not timestamps:
                    actions_to_clean.append(action)
            
            # Remove empty action queues
            for action in actions_to_clean:
                del actions[action]
            
            # Mark empty user entries for removal
            if not actions:
                users_to_clean.append(user_id)
        
        # Remove empty user entries
        for user_id in users_to_clean:
            del _rate_limit_storage[user_id]
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return {"error": str(e)}

def backup_data(backup_type='full'):
    """Create data backup"""
    try:
        from models import Post, Comment, User
        
        backup = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": backup_type,
            "data": {}
        }
        
        if backup_type == 'full' or backup_type == 'users':
            users = User.query.all()
            backup["data"]["users"] = [standardize_user_response(user) for user in users]
        
        if backup_type == 'full' or backup_type == 'content':
            posts = Post.query.all()
            backup["data"]["posts"] = [standardize_post_response(post) for post in posts]
            
            comments = Comment.query.all()
            backup["data"]["comments"] = [standardize_comment_response(comment) for comment in comments]
        
        backup["stats"] = {
            "users_count": len(backup["data"].get("users", [])),
            "posts_count": len(backup["data"].get("posts", [])),
            "comments_count": len(backup["data"].get("comments", []))
        }
        
        return {"success": True, "backup": backup}
    
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return {"success": False, "error": str(e)}

# ===== NOTIFICATION HELPERS =====

def create_notification(user_id, notification_type, title, message, data=None):
    """Create a notification for a user"""
    try:
        notification = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        
        # In a real system, you'd save this to a notifications table
        logger.info(f"Notification created: {notification}")
        
        return {"success": True, "notification": notification}
    
    except Exception as e:
        logger.error(f"Notification creation error: {e}")
        return {"success": False, "error": str(e)}

def send_email_notification(email, subject, template, data=None):
    """Send email notification"""
    try:
        # This would integrate with your email service
        logger.info(f"Email notification sent to {email}: {subject}")
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Email notification error: {e}")
        return {"success": False, "error": str(e)}

# ===== UTILITY CONSTANTS =====

# Common HTTP status codes
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'NO_CONTENT': 204,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'UNPROCESSABLE_ENTITY': 422,
    'TOO_MANY_REQUESTS': 429,
    'INTERNAL_SERVER_ERROR': 500
}

# Common error messages
ERROR_MESSAGES = {
    'INVALID_JSON': 'Request must contain valid JSON',
    'MISSING_FIELDS': 'Missing required fields',
    'UNAUTHORIZED': 'Authentication required',
    'FORBIDDEN': 'Insufficient permissions',
    'NOT_FOUND': 'Resource not found',
    'ALREADY_EXISTS': 'Resource already exists',
    'RATE_LIMITED': 'Rate limit exceeded',
    'SERVER_ERROR': 'Internal server error'
}

# Content validation limits
CONTENT_LIMITS = {
    'POST_TITLE_MIN': 3,
    'POST_TITLE_MAX': 200,
    'POST_CONTENT_MIN': 10,
    'POST_CONTENT_MAX': 10000,
    'COMMENT_CONTENT_MIN': 1,
    'COMMENT_CONTENT_MAX': 1000,
    'USERNAME_MIN': 3,
    'USERNAME_MAX': 20,
    'EMAIL_MAX': 120,
    'PASSWORD_MIN': 6,
    'PASSWORD_MAX': 100,
    'TAGS_MAX': 255
}

# Rate limiting defaults
RATE_LIMITS = {
    'LOGIN_ATTEMPTS': {'limit': 5, 'window': 15},  # 5 attempts per 15 minutes
    'POST_CREATION': {'limit': 10, 'window': 60},  # 10 posts per hour
    'COMMENT_CREATION': {'limit': 50, 'window': 60},  # 50 comments per hour
    'API_GENERAL': {'limit': 1000, 'window': 60},  # 1000 requests per hour
    'SEARCH': {'limit': 100, 'window': 60}  # 100 searches per hour
}

# Cache TTL defaults (in seconds)
CACHE_TTL = {
    'USER_PROFILE': 300,  # 5 minutes
    'POST_LIST': 180,     # 3 minutes
    'COMMENT_LIST': 120,  # 2 minutes
    'STATS': 600,         # 10 minutes
    'SEARCH_RESULTS': 300 # 5 minutes
}

# ===== INITIALIZATION FUNCTION =====

def initialize_utils():
    """Initialize utility functions and perform startup tasks"""
    try:
        logger.info("Initializing utils module...")
        
        # Clear any existing cache
        clear_cache()
        
        logger.info("Utils module initialized successfully")
        
        return True
    
    except Exception as e:
        logger.error(f"Utils initialization error: {e}")
        return False

# Auto-initialize when module is imported
if __name__ != "__main__":
    initialize_utils()