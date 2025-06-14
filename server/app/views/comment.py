from flask import Blueprint,jsonify

comment_bp = Blueprint('user', __name__)

@comment_bp.route('/<int:user_id>', methods=['GET'])

def profile():
    return jsonify ({
        "success" : "Added comment to the comment list"
    })