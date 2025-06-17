from flask import Flask
from .extensions import db, migrate
from . import views

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    views.register_blueprints(app)

    from . import models

    return app
