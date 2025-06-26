from datetime import timedelta
import os
from flask import Flask, request, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp
from views.admin import admin_bp  

app = Flask(__name__)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
app.config["JWT_SECRET_KEY"] = "jwt_secret_key"  # Change this in production!
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=48)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]
app.config["JWT_VERIFY_SUB"] = False

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config["MAIL_USE_SSL"] = False
app.config['MAIL_USERNAME'] = "projectappmail1998@gmail.com"
app.config['MAIL_PASSWORD'] = "hirm xovn cikd jskq"
app.config['MAIL_DEFAULT_SENDER'] = "yourrmail@gmail.com"

# Upload Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize Extensions
db.init_app(app)
migrate = Migrate(app, db)

# ✅ FIXED: More comprehensive CORS configuration
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

mail = Mail(app)
jwt = JWTManager(app)

# ✅ FIXED: Explicit preflight request handling
@app.before_request
def handle_preflight():
    """Handle CORS preflight requests"""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-Requested-With")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,PATCH,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', "true")
        return response

# JWT Event Handlers
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    """Check if JWT token is in blocklist"""
    jti = jwt_payload["jti"]
    return db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar() is not None

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Handle expired tokens"""
    return {"error": "Token has expired", "message": "Please log in again"}, 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Handle invalid tokens"""
    return {"error": "Invalid token", "message": "Please log in again"}, 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    """Handle missing tokens"""
    return {"error": "Authorization token required", "message": "Please log in"}, 401

# Register Blueprints
app.register_blueprint(post_bp, url_prefix="/api/posts")
app.register_blueprint(comment_bp, url_prefix="/api/comments")
app.register_blueprint(user_bp, url_prefix="/api/users")
app.register_blueprint(vote_bp, url_prefix="/api/votes")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")  # ✅ Admin blueprint registered
app.register_blueprint(home_bp)  # No prefix for home routes

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors with JSON response"""
    return {"error": "Resource not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with JSON response"""
    db.session.rollback()
    return {"error": "Internal server error"}, 500

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    return {"error": "File too large"}, 413

def create_upload_dirs():
    """Create necessary upload directories"""
    upload_dirs = [
        'uploads',
        'uploads/avatars', 
        'uploads/temp'
    ]
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)

# Initialize Database and Directories
with app.app_context():
    try:
        db.create_all()
        create_upload_dirs()
        print("✅ Connected to the database and created upload directories.")
        print("✅ Admin blueprint registered at /api/admin")
        
        # ✅ Debug: Print relevant routes to verify they exist
        print("\n📋 API Routes Registration Check:")
        relevant_routes = []
        for rule in app.url_map.iter_rules():
            if '/api/' in rule.rule:
                relevant_routes.append(f"   {rule.methods} {rule.rule}")
        
        # Sort and display routes
        for route in sorted(relevant_routes):
            print(route)
            
        # Check for the specific routes that AdminDashboard needs
        critical_routes = ['/api/users', '/api/posts', '/api/comments', '/api/admin/stats']
        print("\n🔍 Critical AdminDashboard Routes Check:")
        for route in critical_routes:
            found = any(route in r for r in relevant_routes)
            status = "✅ Found" if found else "❌ Missing"
            print(f"   {status}: {route}")
                
    except Exception as e:
        print("❌ Database Error:", e)

# ✅ FIXED: Corrected the if __name__ == "__main__" syntax
if __name__ == "__main__":
    app.run(debug=True)