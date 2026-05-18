import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app import create_app
from models import User, db
from services.auth import hash_password


def seed_admin():
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    app = create_app()
    with app.app_context():
        if User.query.filter_by(email=email).first():
            print("admin already exists")
            return
        user = User(email=email, password_hash=hash_password(password), role="admin")
        db.session.add(user)
        db.session.commit()
        print(f"admin created: {email}")


if __name__ == "__main__":
    seed_admin()
