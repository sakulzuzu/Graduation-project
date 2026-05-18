import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


def _resolve_path(raw_value, default_relative):
    value = os.path.normpath(raw_value or default_relative)
    if os.path.isabs(value):
        return value
    head = value.split(os.sep)[0].lower() if value else ""
    if head == "backend":
        return os.path.normpath(os.path.join(PROJECT_ROOT, value))
    return os.path.normpath(os.path.join(BASE_DIR, value))

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change")
JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE_SECONDS", "7200"))

SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@127.0.0.1:3306/thyroid_ai?charset=utf8mb4",
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

UPLOAD_DIR = _resolve_path(os.getenv("UPLOAD_DIR"), os.path.join("storage", "original"))
PROCESSED_DIR = _resolve_path(os.getenv("PROCESSED_DIR"), os.path.join("storage", "processed"))
HEATMAP_DIR = _resolve_path(os.getenv("HEATMAP_DIR"), os.path.join("storage", "heatmap"))

MODEL_WEIGHTS = _resolve_path(os.getenv("MODEL_WEIGHTS"), os.path.join("models", "thyroid_resnet50.pth"))
MODEL_NAME = os.getenv("MODEL_NAME", "resnet50")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "")
