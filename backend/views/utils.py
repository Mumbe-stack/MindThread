from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import User

def block_check_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Allow preflight requests to pass without checking JWT
        if request.method == "OPTIONS":
            return fn(*args, **kwargs)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        if user.is_blocked:
            return jsonify({"error": "Access denied. Your account is blocked."}), 403

        return fn(*args, **kwargs)
    return wrapper
