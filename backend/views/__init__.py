from flask import Flask
from flask_cors import CORS

from .post import post_bp
from .comment import comment_bp
from .user import user_bp
from .vote import vote_bp
from .home import home_bp
from .auth import auth_bp

def create_app():
    app = Flask(__name__)

    CORS(app, supports_credentials=True)

    app.register_blueprint(post_bp, url_prefix="/api/posts")
    app.register_blueprint(comment_bp, url_prefix="/api/comments")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(vote_bp, url_prefix="/api/votes")
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    return app
