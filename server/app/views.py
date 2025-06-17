from flask import Blueprint, jsonify

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/<int:id>', methods=['GET'])
def get_user(id):
   
    user = {"id": id, "name": f"User{id}", "email": f"user{id}@example.com"}
    return jsonify(user)

def register_blueprints(app):
    app.register_blueprint(users_bp)
