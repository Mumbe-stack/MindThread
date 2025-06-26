from models import User, db
from app import app
from werkzeug.security import generate_password_hash


def seed():
    with app.app_context():
        username = "Admin"

        email = "administrator@gexample.com"
        password = "admin"

        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            print("Username already exists.")
            return

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            print("Email already exists.")
            return
        new_admin = User(username=username, email=email,
                         password=generate_password_hash(password), is_admin=True)
        db.session.add(new_admin)
        db.session.commit()
        print("Admin added  successfully.")


seed()
