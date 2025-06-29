from datetime import timedelta
from flask import send_from_directory
import os
import logging
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp
from views.admin import admin_bp


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


CORS(
    app,
    origins=[
        "https://mindthreadbloggingapp.netlify.app",      
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", 
        "Authorization",
        "Access-Control-Allow-Credentials"
    ],
    supports_credentials=True,
    max_age=3600  
)


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://mindthread_db_56lm_user:Kdjo6KFm6y4jsU3TFEZJ5hcgBF7g8fAC@dpg-d1evccfgi27c7384mvc0-a.oregon-postgres.render.com/mindthread_db_56lm"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 30,
    'max_overflow': 10
}


app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY", 
    "jwt_secre542cc4f32fc0a619979df2b56083fb21c97ea4c9e0e2b7d25779734357a1810486ef0c480c8fb9da1990c602dbf1438b9b6f3fa72716b13baf28612496d8fcd8t_key"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]
app.config["JWT_VERIFY_SUB"] = False
app.config["JWT_ALGORITHM"] = "HS256"


app.config['PROPAGATE_EXCEPTIONS'] = True


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config["MAIL_USE_SSL"] = False
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "projectappmail1998@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "hirm xovn cikd jskq")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER", "projectappmail1998@gmail.com")


app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['UPLOAD_FOLDER'] = 'uploads'


app.config['WTF_CSRF_ENABLED'] = False  
app.config['JSON_SORT_KEYS'] = False


db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)
jwt = JWTManager(app)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(app.root_path, 'uploads')
    return send_from_directory(upload_folder, filename)


# Enhanced JWT Error Handlers
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    
    try:
        jti = jwt_payload["jti"]
        return db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar() is not None
    except Exception as e:
        logger.error(f"Error checking token blocklist: {e}")
        return False

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
   
    logger.warning(f"Expired token accessed by user: {jwt_payload.get('sub', 'unknown')}")
    return jsonify({
        "error": "Token has expired",
        "message": "Please log in again",
        "code": "TOKEN_EXPIRED"
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
   
    logger.warning(f"Invalid token error: {error}")
    return jsonify({
        "error": "Invalid token",
        "message": "Please log in again",
        "code": "TOKEN_INVALID"
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
   
    return jsonify({
        "error": "Authorization token required",
        "message": "Please log in to access this resource",
        "code": "TOKEN_MISSING"
    }), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
   
    logger.warning(f"Revoked token accessed by user: {jwt_payload.get('sub', 'unknown')}")
    return jsonify({
        "error": "Token has been revoked",
        "message": "Please log in again",
        "code": "TOKEN_REVOKED"
    }), 401

@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    
    return jsonify({
        "error": "Fresh token required",
        "message": "Please log in again to access this resource",
        "code": "TOKEN_NOT_FRESH"
    }), 401


@app.errorhandler(400)
def bad_request(error):
   
    logger.warning(f"Bad request: {error}")
    return jsonify({
        "error": "Bad Request",
        "message": "The request could not be understood by the server",
        "code": "BAD_REQUEST"
    }), 400

@app.errorhandler(401)
def unauthorized(error):
   
    return jsonify({
        "error": "Unauthorized",
        "message": "Authentication required",
        "code": "UNAUTHORIZED"
    }), 401

@app.errorhandler(403)
def forbidden(error):
    
    return jsonify({
        "error": "Forbidden",
        "message": "You don't have permission to access this resource",
        "code": "FORBIDDEN"
    }), 403

@app.errorhandler(404)
def not_found(error):
  
    return jsonify({
        "error": "Resource not found",
        "message": "The requested resource was not found",
        "code": "NOT_FOUND"
    }), 404

@app.errorhandler(409)
def conflict(error):
   
    return jsonify({
        "error": "Conflict",
        "message": "The request conflicts with the current state of the resource",
        "code": "CONFLICT"
    }), 409

@app.errorhandler(413)
def too_large(error):
   
    return jsonify({
        "error": "File too large",
        "message": "The uploaded file exceeds the maximum allowed size",
        "code": "FILE_TOO_LARGE"
    }), 413

@app.errorhandler(422)
def unprocessable_entity(error):
    
    return jsonify({
        "error": "Unprocessable Entity",
        "message": "The request was well-formed but contains semantic errors",
        "code": "UNPROCESSABLE_ENTITY"
    }), 422

@app.errorhandler(429)
def too_many_requests(error):
   
    return jsonify({
        "error": "Too Many Requests",
        "message": "Rate limit exceeded. Please try again later.",
        "code": "RATE_LIMIT_EXCEEDED"
    }), 429

@app.errorhandler(500)
def internal_error(error):
   
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


try:

    app.register_blueprint(post_bp, url_prefix="/api")      
    app.register_blueprint(comment_bp, url_prefix="/api")  
    app.register_blueprint(user_bp, url_prefix="/api")      
    app.register_blueprint(vote_bp, url_prefix="/api")    
    app.register_blueprint(auth_bp, url_prefix="/api")     
    app.register_blueprint(admin_bp, url_prefix="/api")     
    app.register_blueprint(home_bp)                        
    logger.info("✅ All blueprints registered successfully")
except Exception as e:
    logger.error(f"❌ Error registering blueprints: {e}")


@app.route('/api/health', methods=['GET'])
def health_check():
  
    try:
      
        db.session.execute('SELECT 1')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "2.0.0",
        "features": {
            "post_approval": True,
            "comment_approval": True,
            "admin_dashboard": True,
            "voting_system": True,
            "like_system": True,
            "user_management": True,
            "content_flagging": True
        },
        "environment": os.environ.get("FLASK_ENV", "production"),
        "timestamp": str(os.times().elapsed) if hasattr(os, 'times') else "unavailable"
    }), 200 if db_status == "healthy" else 503


@app.route('/api/info', methods=['GET'])
def api_info():
   
    return jsonify({
        "name": "MindThread API",
        "version": "2.0.0",
        "description": "A modern blogging platform API with approval system",
        "endpoints": {
            "auth": "/api/auth/*",
            "posts": "/api/posts/*", 
            "comments": "/api/comments/*",
            "users": "/api/users/*",
            "votes": "/api/votes/*",
            "admin": "/api/admin/*",
            "health": "/api/health"
        },
        "features": {
            "post_approval_system": "Posts require admin approval before being visible",
            "comment_approval_system": "Comments require admin approval before being visible", 
            "username_display": "Proper username display throughout the platform",
            "admin_dashboard": "Comprehensive admin dashboard with statistics",
            "voting_system": "Upvote/downvote system for posts and comments",
            "like_system": "Like system for posts and comments",
            "content_flagging": "Admin can flag inappropriate content",
            "user_management": "Admin can manage users (block, promote, etc.)"
        },
        "authentication": "JWT-based authentication with refresh tokens",
        "documentation": "https://mindthread-1.onrender.com/api/docs"
    }), 200


@app.route('/api/status', methods=['GET'])
def api_status():
  
    try:
        from models import User, Post, Comment, Vote, Like
        
   
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        
       
        approval_system_active = hasattr(Post, 'is_approved') and hasattr(Comment, 'is_approved')
        flagging_system_active = hasattr(Post, 'is_flagged') and hasattr(Comment, 'is_flagged')
        
        return jsonify({
            "api_status": "operational",
            "database_status": "connected",
            "approval_system": "active" if approval_system_active else "inactive",
            "flagging_system": "active" if flagging_system_active else "inactive",
            "statistics": {
                "total_users": total_users,
                "total_posts": total_posts,
                "total_comments": total_comments
            },
            "last_checked": str(os.times().elapsed) if hasattr(os, 'times') else "unavailable"
        }), 200
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            "api_status": "degraded",
            "database_status": "error",
            "error": str(e)
        }), 503

def create_upload_dirs():
   
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
            logger.info(f"✅ Created directory: {directory}")
        except Exception as e:
            logger.error(f"❌ Failed to create directory {directory}: {e}")

def validate_environment():
    
    required_vars = []
    warnings = []
    
    
    if not os.environ.get("JWT_SECRET_KEY"):
        warnings.append("JWT_SECRET_KEY not set - using default (not recommended for production)")
    
    if not os.environ.get("DATABASE_URL"):
        warnings.append("DATABASE_URL not set - using default database")
    
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    return len(required_vars) == 0

def check_model_compatibility():
    
    try:
        from models import Post, Comment
        
      
        post_has_approval = hasattr(Post, 'is_approved')
        post_has_flagging = hasattr(Post, 'is_flagged')
        
        
        comment_has_approval = hasattr(Comment, 'is_approved')
        comment_has_flagging = hasattr(Comment, 'is_flagged')
        
        if post_has_approval and comment_has_approval:
            logger.info("✅ Approval system fields found in models")
        else:
            logger.warning("⚠️  Approval system fields missing - run migration script")
            
        if post_has_flagging and comment_has_flagging:
            logger.info("✅ Flagging system fields found in models")
        else:
            logger.warning("⚠️  Flagging system fields missing - run migration script")
            
        return {
            "approval_system": post_has_approval and comment_has_approval,
            "flagging_system": post_has_flagging and comment_has_flagging
        }
        
    except Exception as e:
        logger.error(f"❌ Model compatibility check failed: {e}")
        return {"approval_system": False, "flagging_system": False}


with app.app_context():
    try:
        
        validate_environment()
        
       
        db.create_all()
        logger.info("✅ Database tables created successfully")
        
      
        model_status = check_model_compatibility()
        
       
        create_upload_dirs()
        logger.info("✅ Upload directories created successfully")
        
       
        logger.info("✅ API Routes Registration:")
        relevant_routes = []
        for rule in app.url_map.iter_rules():
            if '/api/' in rule.rule:
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                relevant_routes.append(f"   {methods:<20} {rule.rule}")
        
        for route in sorted(relevant_routes):
            logger.info(route)
        
        
        logger.info("🔍 Critical Routes Check:")
        critical_routes = [
            '/api/login',         
            '/api/register',        
            '/api/posts',           
            '/api/posts/<',         
            '/api/comments',        
            '/api/users',           
            '/api/votes/post',   
            '/api/admin/stats',     
            '/api/health'          
        ]
        
        all_routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        for route in critical_routes:
            found = any(route in r for r in all_routes)
            status = '✅ Found' if found else '❌ Missing'
            logger.info(f"   {status}: {route}")
        
       
        logger.info("🎯 System Status:")
        logger.info(f"   ✅ Database: Connected")
        logger.info(f"   {'✅' if model_status['approval_system'] else '⚠️ '} Approval System: {'Active' if model_status['approval_system'] else 'Inactive'}")
        logger.info(f"   {'✅' if model_status['flagging_system'] else '⚠️ '} Flagging System: {'Active' if model_status['flagging_system'] else 'Inactive'}")
        
        logger.info("✅ MindThread API initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Application initialization error: {e}")
       
        if os.environ.get("FLASK_ENV") == "development":
            raise


@app.before_request
def log_request_info():
    
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        logger.debug(f"Request: {request.method} {request.url}")
        if request.is_json and request.method != 'GET':
            try:
                data = request.get_json()
              
                if data and not any(field in str(data) for field in ['password', 'token', 'secret']):
                    logger.debug(f"JSON Data: {data}")
            except:
                pass

@app.after_request
def after_request(response):
   
  
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
   
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        logger.debug(f"Response: {response.status_code}")
    
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🚀 Starting MindThread API on port {port}")
    logger.info(f"🔧 Debug mode: {debug_mode}")
    logger.info(f"🌐 Environment: {os.environ.get('FLASK_ENV', 'production')}")
    logger.info(f"📊 Features: Approval System, Admin Dashboard, Voting, Likes")
    
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=debug_mode,
        threaded=True
    )