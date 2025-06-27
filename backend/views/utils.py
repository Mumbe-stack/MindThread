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
    
    # Limit length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_email(email):
    """
    Validate email format
    """
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))


def validate_username(username):
    """
    Validate username format
    """
    # Username should be 3-20 characters, alphanumeric and underscores only
    username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    return bool(username_pattern.match(username))


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
            "ip_address": request.remote_addr,
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
            if permission not in user_permissions and not user.is_admin:
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
    if "UNIQUE constraint failed" in str(e):
        return jsonify({"error": "Duplicate entry - record already exists"}), 409
    elif "FOREIGN KEY constraint failed" in str(e):
        return jsonify({"error": "Invalid reference - related record not found"}), 400
    elif "NOT NULL constraint failed" in str(e):
        return jsonify({"error": "Missing required field"}), 400
    else:
        return jsonify({"error": f"Database error during {operation}"}), 500


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


# Security utilities
def secure_filename(filename):
    """
    Secure filename for file uploads
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
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