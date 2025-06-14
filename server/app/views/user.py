from flask import Blueprint,jsonify

user_bp = Blueprint('user', __name__) 

@user_bp.route('/profile')

def profile():
    return jsonify ({
        "success" : "User profile endpoint works"
    })