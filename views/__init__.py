def register_blueprints(app):
    from .main import main_bp
    from .post import post_bp
    from .user import user_bp
    from .vote import vote_bp
    from .comment import comment_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(post_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(vote_bp)
    app.register_blueprint(comment_bp)
