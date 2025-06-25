from datetime import timedelta
import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager

from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp, home_bp
from views.admin import admin_bp  

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "jwt_secret_key"  # Change this in production!
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


app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'


db.init_app(app)
migrate = Migrate(app, db)

CORS(app, supports_credentials=True, origins=["http://localhost:5173"], expose_headers=["Authorization"])

mail = Mail(app)
jwt = JWTManager(app)


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



app.register_blueprint(post_bp, url_prefix="/api/posts")
app.register_blueprint(comment_bp, url_prefix="/api/comments")
app.register_blueprint(user_bp, url_prefix="/api/users")
app.register_blueprint(vote_bp, url_prefix="/api/votes")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")  
app.register_blueprint(home_bp)  



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



def create_upload_dirs():
   
    upload_dirs = [
        'uploads',
        'uploads/avatars',
        'uploads/temp'
    ]
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)



with app.app_context():
    try:
        db.create_all()
        create_upload_dirs()
        print("✅ Connected to the database and created upload directories.")
    except Exception as e:
        print("❌ Database Error:", e)


if __name__ == "__main__":
    app.run(debug=True)