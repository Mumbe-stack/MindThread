from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from views.home import home_bp 

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    from models import User, Post, Comment, Vote

    from views.post import post_bp
    from views.comment import comment_bp
    from views.vote import vote_bp
    from views.user import user_bp

    app.register_blueprint(post_bp, url_prefix="/api/posts")
    app.register_blueprint(comment_bp, url_prefix="/api/comments")
    app.register_blueprint(vote_bp, url_prefix="/api/votes")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(home_bp)

    return app
