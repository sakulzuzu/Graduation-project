import os
import uuid

from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def save_upload(file_storage, target_dir):
    ensure_dir(target_dir)
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    full_path = os.path.join(target_dir, filename)
    file_storage.save(full_path)
    return filename, full_path
