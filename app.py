from flask import Flask
from flask_migrate import Migrate
from models import db
from views import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        try:
            db.create_all()
            print("✅ Connected to DB.")
        except Exception as e:
            print("❌ DB Error:", e)

        from models import User, Post, Comment, Vote

        register_blueprints(app)

    return app
