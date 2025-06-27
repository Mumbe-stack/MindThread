from datetime import timedelta
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp, admin_bp

app = Flask(__name__)


CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173", 
            "https://mindthread-1.onrender.com",  
            "https://mindthreadbloggingapp.netlify.app"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"]
    }
})


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://mindthread_db_56lm_user:Kdjo6KFm6y4jsU3TFEZJ5hcgBF7g8fAC@dpg-d1evccfgi27c7384mvc0-a.oregon-postgres.render.com/mindthread_db_56lm"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config["JWT_SECRET_KEY"] = "jwt_secre542cc4f32fc0a619979df2b56083fb21c97ea4c9e0e2b7d25779734357a1810486ef0c480c8fb9da1990c602dbf1438b9b6f3fa72716b13baf28612496d8fcd8t_key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=48)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]
app.config["JWT_VERIFY_SUB"] = False


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
mail = Mail(app)
jwt = JWTManager(app)

# Additional CORS handling for preflight requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'message': 'CORS preflight successful'})
        origin = request.headers.get('Origin')
        
        # Check if origin is allowed
        allowed_origins = [
            "http://localhost:5173",
            "http://localhost:3000", 
            "http://127.0.0.1:5173",
            "https://mindthread-1.onrender.com",
            "https://mindthreadbloggingapp.netlify.app"
        ]
        
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Accept")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,PATCH,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173", 
        "https://mindthread-1.onrender.com",
        "https://mindthreadbloggingapp.netlify.app"
    ]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    
    response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Accept")
    response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,PATCH,OPTIONS")
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# JWT Event Handlers
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    return db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar() is not None

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {"error": "Token has expired", "message": "Please log in again"}, 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return {"error": "Invalid token", "message": "Please log in again"}, 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return {"error": "Authorization token required", "message": "Please log in"}, 401

# Register Blueprints
app.register_blueprint(post_bp, url_prefix="/api/posts")
app.register_blueprint(comment_bp, url_prefix="/api/comments")
app.register_blueprint(user_bp, url_prefix="/api/users")
app.register_blueprint(vote_bp, url_prefix="/api/votes")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(home_bp)

# Health check endpoint for debugging
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'MindThread API is running',
        'cors_enabled': True,
        'allowed_origins': [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "https://mindthread-1.onrender.com", 
            "https://mindthreadbloggingapp.netlify.app"
        ]
    }), 200

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return {"error": "Resource not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return {"error": "Internal server error"}, 500

@app.errorhandler(413)
def too_large(error):
    return {"error": "File too large"}, 413

# Create Upload Directories
def create_upload_dirs():
    upload_dirs = ['uploads', 'uploads/avatars', 'uploads/temp']
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)

# Initialize Database and Print Routes
with app.app_context():
    try:
        db.create_all()
        create_upload_dirs()
        print("✅ Connected to the database and created upload directories.")
        print("✅ Admin blueprint registered at /api/admin")
        print("✅ CORS configured for frontend domain")

        print("\n📋 API Routes Registration Check:")
        relevant_routes = []
        for rule in app.url_map.iter_rules():
            if '/api/' in rule.rule:
                relevant_routes.append(f"   {rule.methods} {rule.rule}")
        for route in sorted(relevant_routes):
            print(route)

        print("\n🔍 Critical AdminDashboard Routes Check:")
        critical_routes = ['/api/users', '/api/posts',
                           '/api/comments', '/api/admin/stats']
        for route in critical_routes:
            found = any(route in r for r in relevant_routes)
            print(f"   {'✅ Found' if found else '❌ Missing'}: {route}")

        print("\n🌐 CORS Configuration:")
        print("   ✅ Netlify domain: https://mindthreadbloggingapp.netlify.app")
        print("   ✅ Render domain: https://mindthread-1.onrender.com")
        print("   ✅ Local development domains included")

    except Exception as e:
        print("❌ Database Error:", e)

# Run App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)