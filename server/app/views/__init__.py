from .user import user_bp
from .post import post_bp
from .comment import comment_bp
from .main import main_bp


def register_blueprints(app):
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(post_bp, url_prefix='/posts')
    app.register_blueprint(comment_bp, url_prefix='/comments')
    app.register_blueprint(main_bp)
    