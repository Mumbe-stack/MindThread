from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from flask_mail import Message
from datetime import datetime, timezone

from models import db, User, TokenBlocklist

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    
    try:
        data = request.get_json()

        
        if not data or not all(k in data for k in ("username", "email", "password")):
            return jsonify({"error": "Missing required fields"}), 400

        username = data["username"].strip()
        email = data["email"].strip().lower()
        password = data["password"].strip()

       
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 409

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 409

       
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()

    
        try:
            if current_app.extensions.get('mail'):
                msg = Message(
                    "Welcome to MindThread!",
                    recipients=[new_user.email]
                )
                msg.body = f"Hi {new_user.username},\n\nWelcome to MindThread! We're excited to have you onboard.\n\nHappy posting!\nMindThread Team"
                current_app.extensions['mail'].send(msg)
        except Exception as e:
            current_app.logger.warning(f"Email send failed: {e}")

        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed. Please try again."}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

       
        user = User.query.filter_by(email=email).first()

        if not user:
            current_app.logger.warning(f"Login failed: No user found for {email}")
            return jsonify({"error": "Invalid credentials"}), 401

       
        if not check_password_hash(user.password_hash, password):
            current_app.logger.warning(f"Login failed: Password mismatch for {email}")
            return jsonify({"error": "Invalid credentials"}), 401

        
        if user.is_blocked:
            return jsonify({"error": "Your account has been blocked. Contact support."}), 403

       
        access_token = create_access_token(identity=user.id)

        return jsonify({
            "success": True,
            "access_token": access_token,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }), 200

    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed. Please try again."}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if user.is_blocked:
            return jsonify({"error": "Account has been blocked"}), 403

        return jsonify({
            "success": True,
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_blocked": user.is_blocked,
            "created_at": user.created_at.isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Get current user error: {e}")
        return jsonify({"error": "Failed to fetch user data"}), 500


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    
    try:
        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)

       
        blocked_token = TokenBlocklist(jti=jti, created_at=now)
        db.session.add(blocked_token)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh_token():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.is_blocked:
            return jsonify({"error": "User not found or blocked"}), 404

      
        new_token = create_access_token(identity=user_id)

        return jsonify({
            "success": True,
            "access_token": new_token
        }), 200

    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if user.is_blocked:
            return jsonify({"error": "Account has been blocked"}), 403

        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400

        current_password = data.get("current_password", "").strip()
        new_password = data.get("new_password", "").strip()

        if not current_password or not new_password:
            return jsonify({"error": "Current and new password are required"}), 400

       
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({"error": "Current password is incorrect"}), 401

       
        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters"}), 400

        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Change password error: {e}")
        return jsonify({"error": "Failed to change password"}), 500


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    
    return jsonify({
        "message": "Email verification not implemented yet"
    }), 501


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    
    return jsonify({
        "message": "Password reset not implemented yet"
    }), 501