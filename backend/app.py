from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_mail import Mail

from models import db, User, Post, Comment, Vote
from views import register_blueprints
from config import Config
from flask_jwt_extended import JWTManager

mail = Mail()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mail.init_app(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app) 

    with app.app_context():
        try:
            db.create_all()
            print("✅ Connected to DB.")
        except Exception as e:
            print("❌ DB Error:", e)

        register_blueprints(app)

    return app
