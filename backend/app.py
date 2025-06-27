from datetime import timedelta
import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp, admin_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enhanced CORS Configuration
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://mindthread-1.onrender.com",              
                "https://mindthreadbloggingapp.netlify.app",      
                "http://localhost:5173",
                "http://localhost:3000",  # Added for React dev server
                "http://127.0.0.1:5173",  # Added for local development
                "http://127.0.0.1:3000"   # Added for local development
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type", 
                "Authorization", 
                "Access-Control-Allow-Credentials",
                "Access-Control-Allow-Origin"
            ],
            "expose_headers": ["Content-Range", "X-Content-Range"]
        }
    },
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://mindthread_db_56lm_user:Kdjo6KFm6y4jsU3TFEZJ5hcgBF7g8fAC@dpg-d1evccfgi27c7384mvc0-a.oregon-postgres.render.com/mindthread_db_56lm"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 30,
    'max_overflow': 10
}

# Enhanced JWT Configuration
app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY", 
    "jwt_secre542cc4f32fc0a619979df2b56083fb21c97ea4c9e0e2b7d25779734357a1810486ef0c480c8fb9da1990c602dbf1438b9b6f3fa72716b13baf28612496d8fcd8t_key"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # Reduced for better security
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]
app.config["JWT_VERIFY_SUB"] = False
app.config["JWT_ALGORITHM"] = "HS256"

# Enable exception propagation for proper error handling
app.config['PROPAGATE_EXCEPTIONS'] = True

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config["MAIL_USE_SSL"] = False
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "projectappmail1998@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "hirm xovn cikd jskq")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER", "projectappmail1998@gmail.com")

# File Upload Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Security Configuration
app.config['WTF_CSRF_ENABLED'] = False  # Disabled for API
app.config['JSON_SORT_KEYS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)
jwt = JWTManager(app)

# Enhanced JWT Error Handlers
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    """Check if a JWT exists in the blocklist"""
    try:
        jti = jwt_payload["jti"]
        return db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar() is not None
    except Exception as e:
        logger.error(f"Error checking token blocklist: {e}")
        return False

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Handle expired token"""
    logger.warning(f"Expired token accessed by user: {jwt_payload.get('sub', 'unknown')}")
    return jsonify({
        "error": "Token has expired",
        "message": "Please log in again",
        "code": "TOKEN_EXPIRED"
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Handle invalid token"""
    logger.warning(f"Invalid token error: {error}")
    return jsonify({
        "error": "Invalid token",
        "message": "Please log in again",
        "code": "TOKEN_INVALID"
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    """Handle missing token"""
    return jsonify({
        "error": "Authorization token required",
        "message": "Please log in to access this resource",
        "code": "TOKEN_MISSING"
    }), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    """Handle revoked token"""
    logger.warning(f"Revoked token accessed by user: {jwt_payload.get('sub', 'unknown')}")
    return jsonify({
        "error": "Token has been revoked",
        "message": "Please log in again",
        "code": "TOKEN_REVOKED"
    }), 401

@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    """Handle non-fresh token"""
    return jsonify({
        "error": "Fresh token required",
        "message": "Please log in again to access this resource",
        "code": "TOKEN_NOT_FRESH"
    }), 401

# Enhanced Error Handlers
@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    logger.warning(f"Bad request: {error}")
    return jsonify({
        "error": "Bad Request",
        "message": "The request could not be understood by the server",
        "code": "BAD_REQUEST"
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors"""
    return jsonify({
        "error": "Unauthorized",
        "message": "Authentication required",
        "code": "UNAUTHORIZED"
    }), 401

@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors"""
    return jsonify({
        "error": "Forbidden",
        "message": "You don't have permission to access this resource",
        "code": "FORBIDDEN"
    }), 403

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        "error": "Resource not found",
        "message": "The requested resource was not found",
        "code": "NOT_FOUND"
    }), 404

@app.errorhandler(409)
def conflict(error):
    """Handle conflict errors"""
    return jsonify({
        "error": "Conflict",
        "message": "The request conflicts with the current state of the resource",
        "code": "CONFLICT"
    }), 409

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    return jsonify({
        "error": "File too large",
        "message": "The uploaded file exceeds the maximum allowed size",
        "code": "FILE_TOO_LARGE"
    }), 413

@app.errorhandler(422)
def unprocessable_entity(error):
    """Handle unprocessable entity errors"""
    return jsonify({
        "error": "Unprocessable Entity",
        "message": "The request was well-formed but contains semantic errors",
        "code": "UNPROCESSABLE_ENTITY"
    }), 422

@app.errorhandler(429)
def too_many_requests(error):
    """Handle rate limiting errors"""
    return jsonify({
        "error": "Too Many Requests",
        "message": "Rate limit exceeded. Please try again later.",
        "code": "RATE_LIMIT_EXCEEDED"
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    try:
        db.session.rollback()
    except Exception:
        pass
    
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later.",
        "code": "INTERNAL_ERROR"
    }), 500

@app.errorhandler(502)
def bad_gateway(error):
    """Handle bad gateway errors"""
    return jsonify({
        "error": "Bad Gateway",
        "message": "The server received an invalid response from an upstream server",
        "code": "BAD_GATEWAY"
    }), 502

@app.errorhandler(503)
def service_unavailable(error):
    """Handle service unavailable errors"""
    return jsonify({
        "error": "Service Unavailable",
        "message": "The server is temporarily unavailable",
        "code": "SERVICE_UNAVAILABLE"
    }), 503

# Register Blueprints with enhanced error handling
try:
    app.register_blueprint(post_bp, url_prefix="/api/posts")
    app.register_blueprint(comment_bp, url_prefix="/api/comments")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(vote_bp, url_prefix="/api/votes")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(home_bp)
    logger.info("All blueprints registered successfully")
except Exception as e:
    logger.error(f"Error registering blueprints: {e}")

# Health Check Endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "1.0.0",
        "environment": os.environ.get("FLASK_ENV", "production"),
        "timestamp": os.times().elapsed
    }), 200 if db_status == "healthy" else 503

# API Info Endpoint
@app.route('/api/info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        "name": "MindThread API",
        "version": "1.0.0",
        "description": "A modern blogging platform API",
        "endpoints": {
            "auth": "/api/auth",
            "posts": "/api/posts", 
            "comments": "/api/comments",
            "users": "/api/users",
            "votes": "/api/votes",
            "admin": "/api/admin",
            "health": "/api/health"
        },
        "documentation": "https://mindthread-1.onrender.com/api/docs"
    }), 200

def create_upload_dirs():
    """Create necessary upload directories"""
    upload_dirs = [
        'uploads', 
        'uploads/avatars', 
        'uploads/temp',
        'uploads/posts',
        'uploads/documents'
    ]
    for directory in upload_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")

def validate_environment():
    """Validate required environment variables"""
    required_vars = []
    warnings = []
    
    # Check for production environment variables
    if not os.environ.get("JWT_SECRET_KEY"):
        warnings.append("JWT_SECRET_KEY not set - using default (not recommended for production)")
    
    if not os.environ.get("DATABASE_URL"):
        warnings.append("DATABASE_URL not set - using default database")
    
    for warning in warnings:
        logger.warning(warning)
    
    return len(required_vars) == 0

# Application Context Setup
with app.app_context():
    try:
        # Validate environment
        validate_environment()
        
        # Create database tables
        db.create_all()
        logger.info("✅ Database tables created successfully")
        
        # Create upload directories
        create_upload_dirs()
        logger.info("✅ Upload directories created successfully")
        
        # Log registered routes
        logger.info("✅ API Routes Registration:")
        relevant_routes = []
        for rule in app.url_map.iter_rules():
            if '/api/' in rule.rule:
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                relevant_routes.append(f"   {methods:<20} {rule.rule}")
        
        for route in sorted(relevant_routes):
            logger.info(route)
        
        # Check critical routes
        logger.info("🔍 Critical Routes Check:")
        critical_routes = [
            '/api/auth/login',
            '/api/auth/register', 
            '/api/posts',
            '/api/comments',
            '/api/users',
            '/api/admin/stats',
            '/api/health'
        ]
        
        for route in critical_routes:
            found = any(route in r for r in relevant_routes)
            status = '✅ Found' if found else '❌ Missing'
            logger.info(f"   {status}: {route}")
        
        logger.info("✅ Application initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Application initialization error: {e}")
        # Don't exit in production, log error and continue
        if os.environ.get("FLASK_ENV") == "development":
            raise

# Add request logging for debugging
@app.before_request
def log_request_info():
    """Log request information for debugging"""
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        logger.debug(f"Request: {request.method} {request.url}")
        if request.is_json:
            logger.debug(f"JSON Data: {request.get_json()}")

@app.after_request
def after_request(response):
    """Add security headers and log response"""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Log response for debugging
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        logger.debug(f"Response: {response.status_code}")
    
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 Starting MindThread API on port {port}")
    logger.info(f"🔧 Debug mode: {debug_mode}")
    logger.info(f"🌐 Environment: {os.environ.get('FLASK_ENV', 'production')}")
    
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=debug_mode,
        threaded=True
    )