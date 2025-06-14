from flask import Blueprint, jsonify

post_bp = Blueprint('post', __name__)

@post_bp.route('/<int:post_id>', methods=['GET'])

def list_posts():
    return jsonify({
        "success": "List of blog posts",
        
    })