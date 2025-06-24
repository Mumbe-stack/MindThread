from datetime import timedelta
import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager

from models import db, TokenBlocklist
from views import post_bp, comment_bp, user_bp, vote_bp, home_bp, auth_bp

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "jwt_secret_key"
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

# === Init Extensions === #
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)
mail = Mail(app)
jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    return db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar() is not None

app.register_blueprint(post_bp, url_prefix="/api/posts")
app.register_blueprint(comment_bp, url_prefix="/api/comments")
app.register_blueprint(user_bp, url_prefix="/api/users")
app.register_blueprint(vote_bp, url_prefix="/api/votes")
app.register_blueprint(home_bp)
app.register_blueprint(auth_bp, url_prefix="/api/auth")

with app.app_context():
    try:
        db.create_all()
        print("✅ Connected to the database.")
    except Exception as e:
        print("❌ Database Error:", e)

if __name__ == "__main__":
    app.run(debug=True)
