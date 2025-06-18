from flask import Flask
from flask_migrate import Migrate
from models import db
from views import register_blueprints
from flask import jsonify
from flask_jwt_extended import JWTManager

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate = Migrate(app, db)
    
    jwt = JWTManager(app)
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({"error": "Missing or invalid token"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token"}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has been revoked"}), 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Fresh token required"}), 401

    with app.app_context():
        try:
            db.create_all()
            print("✅ Connected to DB.")
        except Exception as e:
            print("❌ DB Error:", e)

        from models import User, Post, Comment, Vote

        register_blueprints(app)

    return app
