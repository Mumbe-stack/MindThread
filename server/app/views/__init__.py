def register blueprints(app):
    from . import main
    from . import auth
    from . import api

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)

   