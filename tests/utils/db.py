import os

from app.init_db import init_db

def create_test_db(db_path: str):
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db(db_path)
