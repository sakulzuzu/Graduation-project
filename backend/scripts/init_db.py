import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app import create_app
from models import db


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        print("db initialized")
