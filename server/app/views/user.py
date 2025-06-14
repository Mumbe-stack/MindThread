from flask import Blueprint,jsonify

user_bp = Blueprint('user', __name__) 

@user_bp.route('/<int:user_id>', methods=['GET'])

def profile():
    return jsonify ({
        "success" : "User profile endpoint works"
    })