from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify
from models import User

def block_check_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = User.query.get(get_jwt_identity())
        if user and user.is_blocked:
            return jsonify({"error": "Access denied. Your account is blocked."}), 403
        return fn(*args, **kwargs)
    return wrapper
