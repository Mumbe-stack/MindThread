# seed.py
from app import app
from models import db, User, Post
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    db.drop_all()
    db.create_all()

    # Create admin user
    admin = User(
        username="Admin",
        email="administrator@example.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True,
    )
    db.session.add(admin)

    # Create sample post
    post = Post(
        title="Welcome to MindThread!",
        content="This is your first post.",
        tags="intro,announcement",
        created_at=datetime.utcnow(),
        user_id=1,
        is_approved=True
    )
    db.session.add(post)

    db.session.commit()
    print("✅ Database seeded successfully.")
